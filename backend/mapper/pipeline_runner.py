"""
pipeline_runner.py — Three-stage queue pipeline for snapshot processing.

Per the user's spec, snapshot processing runs as three INDEPENDENT
worker threads coordinating via two thread-safe queues:

    [Stage 1: Scanner + chunker]
        scrolls the live browser, builds the master tree
        diffs each iteration's added_nodes against the previous
        once a delta is "verified" (next iteration finds no new
            elements at the same patterns), chunks it
        pushes (chunks, instances) onto chunk_queue

    [Stage 2: TF-IDF vectorizer]
        pops verified-delta chunks off chunk_queue
        renders each chunk's shadow-HTML summary text
        adds rows to the global TF-IDF store (incremental,
            token-complete, CUDA-default)
        pushes stream payloads onto stream_queue

    [Stage 3: Streamer + DB writer]
        pops payloads off stream_queue
        forwards them to the WebSocket via on_stream(...)
        commits chunk rows + instance rows to kuzu

Each stage logs ``[stats]`` lines that the streamer multiplexes
into a ``stats`` event so the frontend can show live counters
(nodes streamed, chunks verified, instances persisted).

The three workers share NO state except the queues + the
process-wide global TF-IDF store. They can run in parallel
because:
  * Stage 1 is dominated by Selenium IO + DOM walks (CPU light)
  * Stage 2 is dominated by token interning + sparse matvec
  * Stage 3 is dominated by Cypher upserts + JSON serialization

Sentinel: each stage drains its queue until it sees ``_DONE``,
then puts ``_DONE`` on the next queue and exits. This guarantees
no payloads are lost if the scanner finishes faster than the
TF-IDF stage drains.
"""

from __future__ import annotations

import logging
import queue as stdlib_queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from backend.mapper.pipeline_config import get_config as _get_pipeline_config

logger = logging.getLogger(__name__)


_DONE = object()  # sentinel value for queue termination

# Maximum samples retained per stage for the /api/profile endpoint.
_HISTOGRAM_RING_SIZE = 200


class StageHistogram:
    """Fixed-size ring buffer of per-batch wall-clock durations (ms).

    Used by ``/api/profile`` to return recent per-stage timings without
    unbounded memory growth.  One instance per pipeline stage.
    """

    __slots__ = ("_buf", "_idx", "_count", "_size")

    def __init__(self, size: int = _HISTOGRAM_RING_SIZE):
        self._size = size
        self._buf: List[float] = [0.0] * size
        self._idx = 0
        self._count = 0

    def record(self, duration_ms: float) -> None:
        self._buf[self._idx % self._size] = duration_ms
        self._idx += 1
        if self._count < self._size:
            self._count += 1

    def samples(self) -> List[float]:
        """Return recorded samples in insertion order (oldest first)."""
        if self._count < self._size:
            return self._buf[: self._count]
        start = self._idx % self._size
        return self._buf[start:] + self._buf[:start]

    def summary(self) -> Dict[str, Any]:
        """Return p50 / p95 / p99 / max / count for the /api/profile response."""
        import math
        vals = self.samples()
        if not vals:
            return {"count": 0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
        s = sorted(vals)
        n = len(s)

        def _pct(p: float) -> float:
            k = (p / 100.0) * (n - 1)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return round(s[int(k)], 2)
            return round(s[f] * (c - k) + s[c] * (k - f), 2)

        return {
            "count": n,
            "p50": _pct(50),
            "p95": _pct(95),
            "p99": _pct(99),
            "max": round(s[-1], 2),
        }


@dataclass
class PipelineStats:
    """Live counters that the streamer surfaces to the frontend."""

    iter_count: int = 0          # scan iterations completed
    nodes_streamed: int = 0      # 'nodes' frame total nodes
    deltas_verified: int = 0     # iterations whose delta was confirmed stable
    chunks_built: int = 0        # chunks produced by stage 1
    chunks_vectorized: int = 0   # chunks added to global TF-IDF
    instances_persisted: int = 0  # ChunkInstance rows committed to kuzu
    vocab_size: int = 0          # current global vocab size
    doc_count: int = 0           # current global doc count
    start_time: float = 0.0      # time.time() when the pipeline started
    batches_dropped: int = 0     # chunks dropped due to full queue

    # Per-stage timing histograms (ring buffers).
    hist_tfidf: StageHistogram = field(default_factory=StageHistogram)
    hist_stream: StageHistogram = field(default_factory=StageHistogram)
    hist_persist: StageHistogram = field(default_factory=StageHistogram)

    def snapshot(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time if self.start_time else 0.0
        return {
            "iter_count": self.iter_count,
            "nodes_streamed": self.nodes_streamed,
            "deltas_verified": self.deltas_verified,
            "chunks_built": self.chunks_built,
            "chunks_vectorized": self.chunks_vectorized,
            "instances_persisted": self.instances_persisted,
            "vocab_size": self.vocab_size,
            "doc_count": self.doc_count,
            "elapsed_s": round(elapsed, 1),
        }

    def profile(self) -> Dict[str, Any]:
        """Extended view for ``/api/profile``: includes histogram summaries."""
        base = self.snapshot()
        base["histograms"] = {
            "tfidf_ms": self.hist_tfidf.summary(),
            "ws_stream_ms": self.hist_stream.summary(),
            "persist_ms": self.hist_persist.summary(),
        }
        return base


@dataclass
class _ChunkBatch:
    """One verified-delta payload moving from stage 1 to stage 2."""

    iter_idx: int
    snapshot_id: str
    url: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])  # cross-stage observability tag
    chunks: List[Any] = field(default_factory=list)
    instances: List[Any] = field(default_factory=list)
    replaced_chunk_ids: List[str] = field(default_factory=list)  # for fusion events
    skip_fast_path: bool = False  # when True, skip WS fast-path (TF-IDF/DB only)


@dataclass
class _StreamBatch:
    """A payload ready for the WS + DB writer."""

    iter_idx: int
    snapshot_id: str
    url: str
    trace_id: str = ""  # carried from _ChunkBatch
    chunks: List[Any] = field(default_factory=list)
    instances: List[Any] = field(default_factory=list)
    page_embedding: Any = None


class SnapshotPipeline:
    """Run the three-stage scan/vectorize/stream pipeline.

    The mapper instantiates one ``SnapshotPipeline`` per
    ``snapshot()`` call and uses it to drive the work. Stage 1
    runs INLINE in the calling thread (it owns the WebDriver
    and Selenium isn't thread-safe across drivers anyway);
    stages 2 and 3 run on background threads.
    """

    def __init__(
        self,
        *,
        on_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
        stats_interval_s: Optional[float] = None,
    ):
        cfg = _get_pipeline_config()
        self.on_stream = on_stream
        self.stats = PipelineStats()
        self._stats_interval_s = (
            stats_interval_s if stats_interval_s is not None
            else getattr(cfg, 'stats_emit_interval_s', 0.4)
        )
        self._last_stats_emit_t = 0.0
        queue_maxsize = getattr(cfg, 'queue_maxsize', 256)
        self._chunk_q: "stdlib_queue.Queue[Any]" = stdlib_queue.Queue(queue_maxsize)
        self._stream_q: "stdlib_queue.Queue[Any]" = stdlib_queue.Queue(queue_maxsize)
        self._queue_put_timeout = getattr(cfg, 'queue_put_timeout_s', 0.5)
        self._stream_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        # The vectorize + persist callables are injected so the
        # pipeline doesn't depend on the mapper directly — keeps
        # this file unit-testable.
        self._persist_fn: Optional[Callable[[_StreamBatch], int]] = None
        # Join timeouts from config (used in finish()).
        self._stream_join_timeout = getattr(cfg, 'pipeline_stream_join_timeout_s', 5.0)

    # ------------------------------------------------------------------
    # Wiring (set by mapper before start)
    # ------------------------------------------------------------------

    def set_persist_fn(self, fn: Callable[[_StreamBatch], int]) -> None:
        self._persist_fn = fn

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._persist_fn is None:
            raise RuntimeError(
                "SnapshotPipeline requires persist_fn before start()"
            )
        self.stats.start_time = time.time()
        self._stream_thread = threading.Thread(
            target=self._stream_worker, name="wfh-stream", daemon=True,
        )
        self._stream_thread.start()

    def submit_verified_delta(self, batch: _ChunkBatch) -> None:
        """Stage-1 → stage-2 handoff. Called by the scanner once
        an iteration's chunks have been confirmed stable."""
        if self.on_stream and not batch.skip_fast_path:
            t_stream = time.time()
            try:
                self.on_stream(self._build_chunks_payload(batch))
                if batch.instances:
                    self.on_stream(self._build_instances_payload(batch))
            except Exception:
                logger.exception(f"[trace={batch.trace_id}] [Pipeline-fastpath] on_stream failed")
            dt_stream = time.time() - t_stream
            self.stats.hist_stream.record(dt_stream * 1000.0)
        try:
            stream_batch = _StreamBatch(
                iter_idx=batch.iter_idx,
                snapshot_id=batch.snapshot_id,
                url=batch.url,
                trace_id=batch.trace_id,
                chunks=batch.chunks,
                instances=batch.instances,
            )
            self._stream_q.put_nowait(stream_batch)
            self.stats.deltas_verified += 1
            self.stats.chunks_built += len(batch.chunks)
            self.stats.chunks_vectorized += len(batch.chunks)
            self._maybe_emit_stats()
        except stdlib_queue.Full:
            self.stats.batches_dropped += 1
            logger.warning(
                "[Pipeline] TF-IDF queue full; dropping batch (batch will be recovered by direct store update). "
                "iter %d [trace=%s].",
                batch.iter_idx, batch.trace_id,
            )

    def note_iter(self, n_nodes: int) -> None:
        """Stage-1 progress hook — fires per scan iteration so the
        frontend's stats overlay stays live even when no chunks
        have been verified yet."""
        self.stats.iter_count += 1
        self.stats.nodes_streamed += n_nodes
        self._maybe_emit_stats()

    def finish(self) -> None:
        """Drain the queues and join the workers. Idempotent."""
        if self._stream_thread is None:
            return
        self._stream_q.put(_DONE)
        self._stream_thread.join(timeout=self._stream_join_timeout)
        if self._stream_thread.is_alive():
            logger.warning("[Pipeline] stream worker didn't finish in %.0fs", self._stream_join_timeout)
        self._stream_thread = None
        # Flush a final stats frame with complete=True so the
        # frontend's stats overlay transitions to a green "done" state
        # and auto-hides after a short delay.
        self._emit_stats(force=True, complete=True)
        
        import json
        logger.info(f"[Profiler] Pipeline Profile:\n{json.dumps(self.stats.profile(), indent=2)}")

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    def _emit_log(self, stage: str, message: str) -> None:
        """Forward a one-line per-stage log to the frontend.

        The streamer multiplexes ``log`` frames into the same WS the
        ``stats`` and ``chunks_partial`` frames use, so the GUI can
        scroll a live profiler feed without scraping logs.txt. Stage
        names match the worker thread (``tfidf``, ``stream``, ``scan``)
        so the GUI can color-code them.
        """
        if not self.on_stream:
            return
        try:
            self.on_stream({
                "type": "log",
                "stage": stage,
                "message": message,
                "ts": time.time(),
            })
        except Exception:
            # Never let a log emit kill the worker.
            pass

    def _stream_worker(self) -> None:
        import time
        try:
            while not self._stop_event.is_set():
                item = self._stream_q.get()
                if item is _DONE:
                    break

                tid = getattr(item, 'trace_id', '') or ''
                tag = f"[trace={tid}] " if tid else ""

                # GUI Streaming now happens instantly on the fast-path in submit_verified_delta (#31).
                # Stage 3 is now dedicated purely to background database persistence.

                # Commit. Failures here are logged but don't block the next batch
                # — the global TF-IDF index is the canonical retrieval surface, and individual
                # kuzu rows are best-effort metadata.
                t_persist = time.time()
                try:
                    n = self._persist_fn(item)
                    self.stats.instances_persisted += n
                except Exception:
                    logger.exception("%s[Pipeline-stream] persist failed", tag)
                    self._emit_log("stream", f"{tag}persist failed (see server logs)")
                dt_persist = time.time() - t_persist
                self.stats.hist_persist.record(dt_persist * 1000.0)
                if len(item.chunks) > 0:
                    msg = "%spersisted %d chunks and %d instances in %.3fs" % (
                        tag, len(item.chunks), len(item.instances), dt_persist,
                    )
                    logger.info("[Profiler] " + msg)
                    self._emit_log("stream", msg)

                # Notify GUI that vectorization & persistence for this batch is complete (#31)
                if self.on_stream and item.instances:
                    try:
                        self.on_stream({
                            "type": "instances_indexed",
                            "snapshot_id": item.snapshot_id,
                            "url": item.url,
                            "iter_idx": item.iter_idx,
                            "count": len(item.instances)
                        })
                    except Exception:
                        pass

                self._maybe_emit_stats()
        finally:
            logger.info("[Pipeline-stream] worker exit")
            self._emit_log("stream", "worker exit")

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_chunks_payload(batch: Union[_StreamBatch, _ChunkBatch]) -> Dict[str, Any]:
        payload = {
            "type": "chunks_partial",
            "snapshot_id": batch.snapshot_id,
            "url": batch.url,
            "iter_idx": batch.iter_idx,
            "chunks": [
                c.as_dict() if hasattr(c, "as_dict") else c
                for c in batch.chunks
            ],
        }
        # Include replaced_chunk_ids for fusion events
        if hasattr(batch, 'replaced_chunk_ids') and batch.replaced_chunk_ids:
            payload["replaced_chunk_ids"] = batch.replaced_chunk_ids
        return payload

    @staticmethod
    def _build_instances_payload(batch: Union[_StreamBatch, _ChunkBatch]) -> Dict[str, Any]:
        return {
            "type": "chunk_instances_partial",
            "snapshot_id": batch.snapshot_id,
            "url": batch.url,
            "iter_idx": batch.iter_idx,
            "instances": [
                {
                    "chunk_id": getattr(inst, "chunk_id", None),
                    "instance_id": (
                        inst.instance_id(batch.url) if hasattr(inst, "instance_id") else None
                    ),
                    "instance_idx": getattr(inst, "instance_idx", None),
                    "pattern": getattr(inst, "pattern", None),
                    "absolute_xpath": getattr(inst, "absolute_xpath", None),
                    # DROPPED: html_raw, rendered_text, image_url, link_url fetched lazily via NDJSON
                }
                for inst in batch.instances
            ],
        }

    # ------------------------------------------------------------------
    # Delta event payload builders (REAL_TIME_SCAN_UPDATE §8.3)
    # ------------------------------------------------------------------

    @staticmethod
    def build_chunk_added_payload(
        snapshot_id: str, url: str, chunk: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "type": "chunk_added",
            "snapshot_id": snapshot_id,
            "url": url,
            "chunk": chunk,
        }

    @staticmethod
    def build_chunk_replaced_payload(
        snapshot_id: str, url: str, chunk: Dict[str, Any],
        replaced_chunk_id: str = "",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "type": "chunk_replaced",
            "snapshot_id": snapshot_id,
            "url": url,
            "chunk": chunk,
        }
        if replaced_chunk_id:
            payload["replaced_chunk_id"] = replaced_chunk_id
        return payload

    @staticmethod
    def build_chunk_removed_payload(
        snapshot_id: str, url: str, chunk_id: str,
    ) -> Dict[str, Any]:
        return {
            "type": "chunk_removed",
            "snapshot_id": snapshot_id,
            "url": url,
            "chunk_id": chunk_id,
        }

    # ------------------------------------------------------------------
    # Stats emission
    # ------------------------------------------------------------------

    def _maybe_emit_stats(self) -> None:
        now = time.time()
        if now - self._last_stats_emit_t < self._stats_interval_s:
            return
        self._emit_stats()

    def _emit_stats(self, force: bool = False, complete: bool = False) -> None:
        """Push a ``stats`` frame to the frontend. The frontend's
        stats overlay reads these to display live counters.

        When ``complete=True`` the payload includes a ``complete``
        flag so the frontend can show a green completion badge and
        auto-hide the overlay after a short delay."""
        if not self.on_stream:
            return
        try:
            payload = {"type": "stats", **self.stats.snapshot()}
            if complete:
                payload["complete"] = True
            self.on_stream(payload)
        except Exception:
            logger.exception("[Pipeline] stats emission failed")
        self._last_stats_emit_t = time.time()
