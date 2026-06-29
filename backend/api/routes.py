from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect, Body
import asyncio
import dataclasses
import json
import logging
import threading
import time
from pydantic import BaseModel

logger = logging.getLogger(__name__)
from typing import List, Dict, Any, Optional, Tuple
from backend.database import get_connection
from backend.services.xpath_utils import generalize_xpath, get_parent_xpath
from backend.services.selenium_client import WebBrowserManager
from backend.mapper.mapper import DomMapper
from backend.mapper.label_engine import LabelEngine
import os
import traceback
from fastapi.responses import StreamingResponse

from backend.agentic.fluid_engine import FluidEngine, ToolRegistry, AgentGenerator
from backend.services.embedding_service import EmbeddingService
from backend.analytics.segment_embedder import SegmentEmbedder
from backend.services.chat_service import ChatService
from backend.services.retrieval_stream import RetrievalStreamService
from backend.services.content_distilled_view import ContentDistilledService
from backend.services.workflow_state import WorkflowStateTracker, SnapshotState
from backend.services.ws_replay import WsReplayBuffer
from backend.api.errors import WorkflowError
from backend.api.ws_frames import (
    FrameType,
    Provenance,
    make_frame,
    next_frame_seq,
    reset_frame_seq,
    build_umap_canonical,
    build_concept_index_update,
    build_purge_workspace,
    build_apparition_hint,
    build_done,
    stamp_provenance,
)

_chat_service = None
_retrieval_stream = None

def _get_services():
    global _chat_service, _retrieval_stream
    if _chat_service is None:
        conn = get_connection()
        embedder = EmbeddingService()
        segment_embedder = SegmentEmbedder(embedder, conn)
        tool_reg = ToolRegistry()
        agent_gen = AgentGenerator()
        fluid_engine = FluidEngine(tool_reg, agent_gen)
        _chat_service = ChatService(conn, embedder, segment_embedder, fluid_engine)
        _retrieval_stream = RetrievalStreamService(conn, embedder, segment_embedder)
    return _chat_service, _retrieval_stream


# Dedicated chunk-side embedder: the stored ``ChunkInstance.embedding`` rows
# were produced by ``ChunkInstanceEmbedder()`` defaults (nomic-v1 GGUF on
# GPU). Retrieval queries MUST use the same model -- otherwise cosine
# scores between the query vector and stored vectors are meaningless.
# ``_chat_service`` holds an ``EmbeddingService()`` that defaults to v1.5,
# which is a different model. Keep these singletons separate.
_chunk_embedder = None


def _get_chunk_embedder():
    """Return a cached ``ChunkInstanceEmbedder`` (nomic-v1 GGUF GPU).

    Lazy-loaded so the FastAPI boot doesn't pay the GPU model load cost
    when the user never opens the projector. First call can take a few
    seconds as the Nomic model is brought up.
    """
    global _chunk_embedder
    if _chunk_embedder is None:
        from backend.services.chunk_instance_embedder import ChunkInstanceEmbedder
        _chunk_embedder = ChunkInstanceEmbedder()
    return _chunk_embedder

# Safe import of LCA service (may not exist in all setups)
try:
    from backend.services.lca_search import compute_lca_for_labeled_nodes
except ImportError:
    def compute_lca_for_labeled_nodes():
        pass

SNAPSHOT_INDEX = 0
LAST_SNAPSHOT_ROOT_ID = None
# Running X offset for snapshot spacing — accumulates each graph's bounding radius
_cumulative_offset_x: float = 0.0

# Per-snapshot WS frame queues. We use ``asyncio.Queue`` so the WS
# coroutine can ``await q.get()`` directly — no 50 ms polling sleep on
# every drain. Worker threads push via
# ``_event_loop.call_soon_threadsafe(q.put_nowait, frame)`` (see
# ``_ws_push`` below) which is thread-safe and wakes the awaiter
# immediately. The previous design (stdlib ``Queue`` + ``get_nowait`` +
# ``await asyncio.sleep(0.05)``) added up to 50 ms of latency per
# frame, dominating WS responsiveness during fast-burst streams.
_stream_queues: Dict[int, "asyncio.Queue"] = {}
_stream_lock = threading.Lock()

# W11 — Workspace-scoped WS queues (keyed by workspace_id string).
# Distinct from ``_stream_queues`` which is keyed by snapshot_id int.
# Frames that are not scan-bound (concept_index_update, agent_token,
# umap_canonical broadcast post-scan, purge_workspace, etc.) flow
# through here. The two queue sets coexist; the broadcast dispatch
# below pushes to both so legacy snapshot-WS listeners still receive
# everything they did before W11.
_workspace_queues: Dict[str, "asyncio.Queue"] = {}
_workspace_lock = threading.Lock()

# Captured at app startup from the FastAPI lifespan. Worker threads
# call into this loop via ``call_soon_threadsafe`` to enqueue frames
# from outside the event-loop thread.
_event_loop: Optional[asyncio.AbstractEventLoop] = None

# Backpressure counter — ``_ws_push`` increments per drop so an
# operator can see slow-consumer rate via ``GET /api/health`` or logs.
# Bounded queues default to ``settings.ws_queue_max`` items each;
# overflow drops the *new* frame (head stays, tail trimmed) so the
# consumer always sees a contiguous prefix rather than gaps in the
# middle. The replay buffer (``WsReplayBuffer``) backstops gaps for
# clients that re-connect with a ``resume`` seq.
_ws_drop_counts: Dict[str, int] = {}
_ws_drop_lock = threading.Lock()

# Alarm-level memory — we emit one structured ``logger.warning`` per
# queue per threshold crossing, NOT per dropped frame. Without this
# the log would fill with thousands of identical lines under a slow-
# consumer event. Thresholds form a step-function; once a queue
# crosses N drops we mark its level, and only emit again when it
# crosses the NEXT step up.
_DROP_ALARM_LEVELS = (1, 10, 100, 1000, 10000)
_ws_drop_alarm_high: Dict[str, int] = {}   # queue_key → highest threshold already alerted


def _new_ws_queue() -> "asyncio.Queue":
    """Create a bounded asyncio queue using the configured maxsize.
    Centralised so workspace + snapshot queues share the same shape."""
    from backend.services.settings import get_settings
    return asyncio.Queue(maxsize=int(get_settings().ws_queue_max))


# ---------------------------------------------------------------------------
# Idempotency cache for concept mutation retries
#
# Client supplies ``idempotency_key`` (UUID) on PATCH/POST; backend
# caches the response by (workspace_id, concept_id, key) for
# ``settings.idempotency_ttl_sec``. A retry within the window returns
# the cached response directly without re-firing the lifecycle chain,
# preventing duplicate broadcasts + log entries on flaky networks.
# ---------------------------------------------------------------------------

_idempotency_cache: Dict[str, "tuple"] = {}      # cache_key → (expires_at, response_dict)
_idempotency_lock = threading.Lock()


def _idempotency_lookup(
    workspace_id: str, concept_id: str, key: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Return the cached response for this key, or None if absent /
    expired. Side-effect: prunes expired entries."""
    if not key:
        return None
    cache_key = f"{workspace_id or '_default'}::{concept_id or '_'}::{key}"
    now = time.time()
    with _idempotency_lock:
        # Lazy prune: drop expired entries on every lookup. Bounded by
        # the request rate, so cheap.
        expired = [k for k, (exp, _) in _idempotency_cache.items() if exp <= now]
        for k in expired:
            _idempotency_cache.pop(k, None)
        entry = _idempotency_cache.get(cache_key)
        if entry is None:
            return None
        return entry[1]


def _idempotency_store(
    workspace_id: str, concept_id: str, key: Optional[str],
    response: Dict[str, Any],
) -> None:
    """Cache the response for ``settings.idempotency_ttl_sec``.

    Evicts the oldest 25 % when the cache hits
    ``settings.idempotency_cache_max`` to bound memory under retry
    storms. Insertion-order eviction is FIFO-style — works because
    every entry has the same TTL, so oldest-insert ≈ oldest-expiring.
    """
    if not key:
        return
    cache_key = f"{workspace_id or '_default'}::{concept_id or '_'}::{key}"
    from backend.services.settings import get_settings
    settings = get_settings()
    ttl = float(settings.idempotency_ttl_sec)
    cap = int(settings.idempotency_cache_max)
    with _idempotency_lock:
        if len(_idempotency_cache) >= cap:
            # Evict oldest 25 % so we don't pay the eviction cost on
            # every store under sustained pressure.
            evict_n = max(1, cap // 4)
            for k in list(_idempotency_cache.keys())[:evict_n]:
                _idempotency_cache.pop(k, None)
        _idempotency_cache[cache_key] = (time.time() + ttl, response)


def get_ws_drop_counts() -> Dict[str, int]:
    """Snapshot of how many frames have been dropped per queue id
    since process start. Returned by ``/api/health`` so an operator
    can spot slow consumers."""
    with _ws_drop_lock:
        return dict(_ws_drop_counts)


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called from main.py's lifespan to capture the running event loop.

    Worker callbacks need this reference to schedule WS pushes onto
    the loop from a non-asyncio thread. Without it, ``put_nowait``
    against an ``asyncio.Queue`` from a worker thread is undefined
    behavior.
    """
    global _event_loop
    _event_loop = loop


def _ws_push(snapshot_id: int, payload: Dict[str, Any]) -> None:
    """Thread-safe push of a WS frame from a worker thread.

    No-op if neither a snapshot queue nor a workspace queue is ready;
    drops are safe because the replay buffer + initial-frame
    contracts cover reconnection.

    W1 (§11.4): stamp ``frame_seq`` on any payload that doesn't
    already carry one. Sequence counter is per-snapshot_id (legacy)
    so frames within a scan are ordered.

    W11: if the payload carries a ``workspace_id``, ALSO route it to
    the workspace-scoped queue so non-scan frames (concept_index_update,
    agent_token, post-scan umap_canonical, purge_workspace) reach
    workspace WS subscribers. The dual-routing means a single emit
    reaches both the active scan-WS listener (if any) and the
    long-lived workspace-WS listener.
    """
    if isinstance(payload, dict) and "frame_seq" not in payload:
        payload["frame_seq"] = next_frame_seq(str(snapshot_id))
    loop = _event_loop
    if loop is None:
        return

    def _enqueue_or_drop(queue: "asyncio.Queue", drop_key: str) -> None:
        """Push the frame onto ``queue``. If the queue is at capacity
        (slow / disconnected consumer), drop the new frame, bump the
        per-queue counter, and (on each new threshold crossing) emit
        a single ``logger.warning`` so operators see the problem at
        the right severity without log spam. The replay buffer covers
        any frames a client genuinely needs to recover via
        ``?resume=<seq>``.
        """
        def _put():
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                with _ws_drop_lock:
                    new_count = _ws_drop_counts.get(drop_key, 0) + 1
                    _ws_drop_counts[drop_key] = new_count
                    # Step-function alarm: emit ONCE per crossing.
                    prior_level = _ws_drop_alarm_high.get(drop_key, 0)
                    crossed = None
                    for level in _DROP_ALARM_LEVELS:
                        if new_count >= level > prior_level:
                            crossed = level
                            _ws_drop_alarm_high[drop_key] = level
                    if crossed is not None:
                        logger.warning(
                            "WS backpressure: queue %s crossed %d drops "
                            "(qsize=%d/%d). Slow consumer or disconnected client.",
                            drop_key, crossed,
                            queue.qsize(), queue.maxsize,
                        )
        try:
            loop.call_soon_threadsafe(_put)
        except RuntimeError:
            pass

    # Snapshot-scoped routing (legacy).
    q = _stream_queues.get(snapshot_id)
    if q is not None:
        _enqueue_or_drop(q, f"snapshot:{snapshot_id}")

    # Workspace-scoped routing (W11). Frames without workspace_id
    # are scan-internal (chunk_added etc.) and skip this path; frames
    # with workspace_id reach the long-lived workspace WS.
    ws_id = payload.get("workspace_id") if isinstance(payload, dict) else None
    if ws_id is not None:
        wq = _workspace_queues.get(str(ws_id))
        if wq is None and ws_id != "_default":
            # Fall back to the default workspace queue if the
            # explicit one doesn't exist — broadcasts on "_default"
            # are the common case when only one workspace is active.
            wq = _workspace_queues.get("_default")
        if wq is not None:
            _enqueue_or_drop(wq, f"workspace:{ws_id}")

_ws_replay = WsReplayBuffer()

router = APIRouter()

class LabelRequest(BaseModel):
    xpath: str
    label: str

class NodeData(BaseModel):
    xpath: str
    tag: str
    properties: str = "{}"

class GraphIngestRequest(BaseModel):
    nodes: List[NodeData]
    html: str = ""
    snapshot_id: int = 0

class NodeUpdateRequest(BaseModel):
    id: str
    status: str = None
    tags: List[str] = None

@router.post("/upload")
def ingest_dom(req: GraphIngestRequest):
    """
    Ingests parsed DOM nodes into Kuzu graph database.
    """
    conn = get_connection()

    # Simple transaction to insert nodes
    for node in req.nodes:
        node_id = f"snap_{req.snapshot_id}_{node.xpath}"
        conn.execute(
            "MERGE (n:DomNode {node_id: $node_id}) "
            "SET n.xpath = $xpath, n.tag = $tag, n.label = '', n.is_user_labeled = false, n.attributes = $props;",
            parameters={"node_id": node_id, "xpath": node.xpath, "tag": node.tag, "props": node.properties}
        )

        # Build ChildOf relationship
        parent_xpath = get_parent_xpath(node.xpath)
        if parent_xpath and parent_xpath != "/":
            parent_id = f"snap_{req.snapshot_id}_{parent_xpath}"
            conn.execute(
                "MATCH (c:DomNode {node_id: $child_id}), (p:DomNode {node_id: $parent_id}) "
                "MERGE (c)-[:ChildOf]->(p);",
                parameters={"child_id": node_id, "parent_id": parent_id}
            )

    return {"status": "success", "nodes_ingested": len(req.nodes)}

@router.post("/label")
def apply_label(req: LabelRequest):
    """
    Applies a label to an absolute XPath, and propagates it to all structurally
    matching XPaths (ignoring list indices).
    """
    conn = get_connection()
    general_pattern = generalize_xpath(req.xpath)

    # 1. First, find all nodes that match this general pattern and label them
    res = conn.execute("MATCH (n:DomNode) RETURN n.xpath;")
    matching_xpaths = []

    while res.has_next():
        xpath = res.get_next()[0]
        if generalize_xpath(xpath) == general_pattern:
            matching_xpaths.append(xpath)

    # Update them all
    for xp in matching_xpaths:
        conn.execute(
            "MATCH (n:DomNode {xpath: $xpath}) SET n.label = $label, n.is_user_labeled = true;",
            parameters={"xpath": xp, "label": req.label}
        )

    # 2. Trigger LCA grouping
    compute_lca_for_labeled_nodes()

    return {"status": "success", "modified_count": len(matching_xpaths), "generalized_xpath": general_pattern}

@router.post("/update")
def update_node(req: NodeUpdateRequest):
    """
    Updates a DOM node's review status by node_id.
    """
    conn = get_connection()
    if req.status is not None:
        is_labeled = req.status == 'yes'
        try:
            conn.execute(
                "MATCH (n:DomNode {node_id: $nid}) SET n.is_user_labeled = $labeled;",
                parameters={"nid": req.id, "labeled": is_labeled}
            )
        except Exception as e:
            logger.warning("API update node %s failed: %s", req.id, e)
            return {"status": "error", "message": str(e)}
    return {"status": "success", "id": req.id}

@router.get("/graph")
def get_graph():
    """
    Returns the Kuzu subgraph of labeled components.
    """
    conn = get_connection()
    res = conn.execute("MATCH (n:DomNode)-[r]->(m:DomNode) RETURN n.xpath, n.label, label(r), m.xpath;")

    edges = []
    nodes = set()

    while res.has_next():
        row = res.get_next()
        edges.append({
            "source": row[0],
            "source_label": row[1],
            "rel": row[2],
            "target": row[3]
        })
        nodes.add((row[0], row[1]))
        nodes.add((row[3], "")) # Target node, maybe no label

    # Also grab standalone labeled nodes
    res2 = conn.execute("MATCH (n:DomNode) WHERE n.is_user_labeled = true RETURN n.xpath, n.label;")
    while res2.has_next():
        row = res2.get_next()
        nodes.add((row[0], row[1]))

    return {
        "nodes": [{"id": n[0], "label": n[1]} for n in nodes],
        "links": [{"source": e["source"], "target": e["target"], "type": e["rel"]} for e in edges]
    }

def _fetch_nodes_for_snapshot(snapshot_id: int = None, limit: int = 2000):
    """Helper method to fetch layout bounds and nodes dynamically decoupled from permanent storage."""
    conn = get_connection()

    # 1. Fetch core semantic properties (Coordinates dropped from Graph DB schema)
    query = "MATCH (n:DomNode) "
    params = {}
    if snapshot_id is not None:
        query += "WHERE n.snapshot_id = $snap_id "
        params["snap_id"] = snapshot_id

    query += "RETURN n.node_id, n.label, n.is_user_labeled, n.tag, n.page_url, n.layout_x, n.layout_y, n.layout_z LIMIT $limit;"
    params["limit"] = limit

    try:
        res = conn.execute(query, parameters=params)
    except Exception as e:
        logger.warning("API native node matching failed: %s", e)
        return {"nodes": [], "links": []}

    nodes = []
    while res.has_next():
        row = res.get_next()
        nodes.append({
            "id": row[0],
            "name": row[1] if row[1] else row[3], # display tag if label is empty
            "status": "yes" if row[2] else "unreviewed",
            "location": row[3], # tag
            "url": row[4],
            "tags": [row[1]] if row[1] else [],
            "x": float(row[5]) if row[5] is not None else 0.0,
            "y": float(row[6]) if row[6] is not None else 0.0,
            "z": float(row[7]) if row[7] is not None else 0.0,
        })

    links = []
    try:
        # Fetch structural DOM lines
        struct_query = "MATCH (c:DomNode)-[:ChildOf]->(p:DomNode) "
        if snapshot_id is not None:
            struct_query += "WHERE c.snapshot_id = $snap_id AND p.snapshot_id = $snap_id "
        struct_query += "RETURN c.node_id, p.node_id LIMIT $limit;"

        struct_res = conn.execute(struct_query, parameters=params)
        while struct_res.has_next():
            row = struct_res.get_next()
            links.append({"source": row[0], "target": row[1], "type": "structure"})

        # Fetch chronological Sequence Links
        seq_query = "MATCH (c:DomNode)-[:SequenceLink]->(p:DomNode) "
        if snapshot_id is not None:
            seq_query += "WHERE c.snapshot_id = $snap_id AND p.snapshot_id = $snap_id "
        seq_query += "RETURN c.node_id, p.node_id LIMIT $limit;"

        seq_res = conn.execute(seq_query, parameters=params)
        while seq_res.has_next():
            row = seq_res.get_next()
            links.append({"source": row[0], "target": row[1], "type": "sequence"})
    except Exception as e:
        logger.warning("API native link loading failed: %s", e)

    return {"nodes": nodes, "links": links}

@router.get("/nodes")
def get_nodes(snapshot_id: int = None, limit: int = 5000):
    """
    Returns all DOM nodes with their layout coordinates for the 3D GUI.
    """
    logger.info("API /nodes endpoint requested")
    payload = _fetch_nodes_for_snapshot(snapshot_id, limit)
    logger.info("API /nodes returning %d nodes + %d links",
                len(payload['nodes']), len(payload['links']))
    return payload

@router.websocket("/ws/workspace/{workspace_id}")
async def websocket_workspace_stream(websocket: WebSocket, workspace_id: str):
    """W11 — Workspace-scoped WS for non-scan frames.

    Carries the frames W5 (concept_index_update), W7 (umap_canonical
    after non-scan triggers), W10 (agent_token), and the
    purge_workspace event use. Long-lived: stays open across scans;
    coexists with the snapshot WS at /ws/nodes/{snapshot_id}.

    On connect, the backend emits an initial workspace bootstrap
    payload (current ConceptIndex slot list + current LayoutFrame)
    so the frontend can hydrate immediately without REST round-trips.
    """
    await websocket.accept()
    ws_key = workspace_id or "_default"
    logger.info("WS workspace client connected for %s", ws_key)

    # Yield control to the event loop so the accept-response flushes
    # to the wire BEFORE the heavy bootstrap below runs. Without this
    # yield, Starlette can buffer the handshake response until the
    # next ``await`` in this coroutine — and the bootstrap below does
    # synchronous heavy work (ConceptIndex / nomic embedder / layout)
    # that takes seconds. The client times out waiting for the
    # handshake to finish even though it's logically complete on the
    # server side. ``asyncio.sleep(0)`` is the cheapest yield.
    import asyncio as _asyncio
    await _asyncio.sleep(0)

    with _workspace_lock:
        if ws_key not in _workspace_queues:
            _workspace_queues[ws_key] = _new_ws_queue()
    q = _workspace_queues[ws_key]

    # Bootstrap: ship current ConceptIndex slots + LayoutFrame so the
    # frontend can render the workspace's current state immediately.
    #
    # The heavy parts (nomic embedder load on first ConceptIndex touch,
    # foundation_fixtures create_concept inserts, layout get_frame) are
    # synchronous and would block the asyncio event loop for several
    # seconds on a cold workspace — meanwhile every REST request to
    # /api/concepts, /api/health, etc. queues behind. We offload the
    # bootstrap to the default executor so the event loop stays
    # responsive; the WS sends are still awaited after the executor
    # call so the frames go out in the right order.
    loop = _asyncio.get_running_loop()

    def _bootstrap_blocking():
        from backend.services.concept_index_service import get_concept_index_service
        from backend.services.layout_service import get_layout_service
        from backend.services.foundation_fixtures import ensure_foundation_fixtures
        ge = _get_graph_editor()
        ci = get_concept_index_service(broadcast=_ws_push, graph_editor=ge)
        # W11b — idempotent fixture ensure (Database, WebBrowser).
        ensure_foundation_fixtures(
            ge, workspace_id="" if ws_key == "_default" else ws_key,
            concept_index=ci,
        )
        slots = ci.list_slots(workspace_id="" if ws_key == "_default" else ws_key)
        layout = get_layout_service(broadcast=_ws_push)
        frame = layout.get_frame(workspace_id="" if ws_key == "_default" else ws_key)
        return slots, frame

    try:
        slots, frame = await loop.run_in_executor(None, _bootstrap_blocking)
        if slots:
            from backend.api.ws_frames import build_concept_index_update
            await websocket.send_json(build_concept_index_update(
                workspace_id=ws_key,
                updates={cid: s.to_broadcast_dict() for cid, s in slots.items()},
            ))
        if frame is not None and frame.coords:
            from backend.api.ws_frames import build_umap_canonical
            await websocket.send_json(build_umap_canonical(
                workspace_id=ws_key,
                coords=frame.coords,
                url_roots=frame.url_roots,
                provenance=frame.provenance,
            ))
    except Exception as e:
        logger.warning("WS workspace bootstrap failed: %s", e)

    # W35 — bidirectional WS: send outgoing frames AND consume
    # client-initiated frames (spine_delta, future user-action
    # telemetry). The recv loop runs as a background task so the
    # main send loop doesn't block on it.
    async def _consume_client_frames():
        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    frame = json.loads(msg)
                except Exception:
                    continue
                ft = (frame or {}).get("type")
                if ft == "spine_delta":
                    # W35 / §8D.27 — write the visible-row delta to
                    # the active AgentState's zone_of_influence so
                    # any running meta-cognition node can read what
                    # the user is currently attending to.
                    try:
                        from backend.services.agent_runtime import (
                            apply_spine_delta_to_active_agents,
                        )
                        apply_spine_delta_to_active_agents(
                            graph_editor=_get_graph_editor(),
                            workspace_id=ws_key if ws_key != "_default" else "",
                            popped=list(frame.get("popped") or []),
                            folded=list(frame.get("folded") or []),
                            push_fn=_ws_push,
                        )
                    except Exception as e:
                        logger.warning("WS workspace spine_delta apply failed: %s", e)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning("WS workspace recv error: %s", e)

    recv_task = asyncio.create_task(_consume_client_frames())

    try:
        while True:
            payload = await q.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        logger.info("WS workspace client disconnected for %s", ws_key)
    except Exception as e:
        logger.warning("WS workspace error: %s", e)
    finally:
        recv_task.cancel()
        with _workspace_lock:
            _workspace_queues.pop(ws_key, None)


@router.websocket("/ws/nodes/{snapshot_id}")
async def websocket_nodes_stream(websocket: WebSocket, snapshot_id: int, resume: int = 0):
    """
    Streams deduplicated DOM nodes to the frontend in real-time.
    Reads from a thread-safe queue fed by the background scanner callback.
    Supports ?resume=<seq> for resilient reconnection.
    """
    await websocket.accept()
    logger.info("WebSocket client connected for snapshot %s", snapshot_id)

    # Catch up from replay buffer if resuming
    if resume > 0:
        try:
            missed_frames = _ws_replay.frames_since(str(snapshot_id), resume)
            for frame in missed_frames:
                await websocket.send_json(frame)
            logger.info("WebSocket replayed %d frames for snapshot %s",
                        len(missed_frames), snapshot_id)
        except ValueError as e:
            if str(e) == "ws_resume_expired":
                await websocket.close(code=4000, reason="ws_resume_expired")
                return

    # Ensure a queue exists for this snapshot (scanner may not have started yet)
    with _stream_lock:
        if snapshot_id not in _stream_queues:
            _stream_queues[snapshot_id] = _new_ws_queue()
    q = _stream_queues[snapshot_id]

    try:
        while True:
            # Native asyncio.Queue: blocks until a worker pushes via
            # ``call_soon_threadsafe(q.put_nowait, ...)``. No polling
            # sleep — the await wakes within microseconds of arrival.
            payload = await q.get()
            await websocket.send_json(payload)
            if payload.get("type") == "done":
                logger.info("WebSocket scan done for snapshot %s, closing", snapshot_id)
                return
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for snapshot %s", snapshot_id)
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        with _stream_lock:
            _stream_queues.pop(snapshot_id, None)

@router.get("/profile")
def get_pipeline_profile():
    """Returns the timing histograms from the most recent active pipeline (#19)."""
    mapper = _get_mapper()
    if hasattr(mapper, 'pipeline') and mapper.pipeline:
        return mapper.pipeline.stats.profile()
    return {"status": "No active pipeline to profile."}

@router.get("/details/{node_id:path}")
def get_node_details(node_id: str):
    """
    Returns extended details for a specific DOM node by node_id.
    """
    conn = get_connection()
    query = "MATCH (n:DomNode) WHERE n.node_id = $nid RETURN n.node_id, n.label, n.html_raw, n.tag, n.depth, n.page_url LIMIT 1;"

    try:
        res = conn.execute(query, parameters={"nid": node_id})
    except Exception as e:
        logger.warning("API fetch details for %s failed: %s", node_id, e)
        return {"id": node_id, "name": "Unknown", "description": "Query error.", "location": "", "website": "", "status": "unreviewed", "tags": []}

    if res.has_next():
        row = res.get_next()
        return {
            "id": row[0],
            "name": row[1] if row[1] else row[3],
            "description": row[2] if row[2] else "No HTML captured.",
            "location": f"Depth: {row[4]} | Tag: {row[3]}",
            "website": row[5] or "",
            "status": "yes" if row[1] in ("yes", "no") else "unreviewed",
            "tags": [],
        }
    return {"id": node_id, "name": "Unknown", "description": "Node not found in database.", "location": "", "website": "", "status": "unreviewed", "tags": []}


# ======================================================================
# MAPPER-BASED SNAPSHOT (primary path)
# ======================================================================

# Shared mapper instance (initialized lazily)
_mapper: DomMapper = None
_mapper_lock = threading.Lock()
_mapper_offset_x: float = 0.0
_browser_manager = None


def _get_mapper() -> DomMapper:
    """Get or create the shared DomMapper instance."""
    global _mapper, _browser_manager
    with _mapper_lock:
        if _mapper is None:
            _mapper = DomMapper(driver=None)
            
            # Always ensure the driver is fresh and healthy before returning
            if os.environ.get("NO_WEBDRIVER") != "1":
                try:
                    if _browser_manager is None:
                        _browser_manager = WebBrowserManager()
                    _mapper.driver = _browser_manager.get_driver()
                except Exception as e:
                    logger.warning("API verify WebDriver health failed: %s", e)
    return _mapper

def shutdown_browser():
    """Cleanly close the browser manager on server shutdown."""
    global _browser_manager
    if _browser_manager:
        try:
            _browser_manager.close()
        except Exception as e:
            logger.warning("API closing browser failed: %s", e)

_workflow_state = WorkflowStateTracker()

_content_distilled_svc = None
_content_distilled_lock = threading.Lock()

def _get_content_distilled_svc() -> ContentDistilledService:
    """Get or create the shared ContentDistilledService instance."""
    global _content_distilled_svc
    with _content_distilled_lock:
        if _content_distilled_svc is None:
            mapper = _get_mapper()
            _content_distilled_svc = ContentDistilledService(mapper, state_tracker=_workflow_state)
    return _content_distilled_svc

class MapperLabelRequest(BaseModel):
    url: str
    xpath: str
    label: str
    snapshot_id: str = None
    auto_commute: bool = True
    auto_lca: bool = True
    idempotency_key: str = None

class LabelBatchRequest(BaseModel):
    url: str
    snapshot_id: str = None
    label: str
    xpaths: List[str]
    auto_commute: bool = True
    auto_lca: bool = True
    idempotency_key: str = None


class StructureTagRequest(BaseModel):
    url: str
    tag_name: str
    label_group: str
    description: str = ''

class DomTextSearchRequest(BaseModel):
    query: str
    url: str = ''
    snapshot_id: Optional[str] = None
    limit: int = 50

class CommutationRequest(BaseModel):
    url: str
    xpath: str
    snapshot_id: Optional[str] = None


@router.get("/scan_status")
def get_scan_status():
    """Return whether a scan is currently active and which WebSocket to use.

    The frontend calls this on page load to detect scans started externally
    (e.g. via scripts/scan.py in backend-delegation mode) and auto-connect
    to the live WebSocket stream without the user clicking Scan.

    Response::

        {
            "active":      true | false,
            "snapshot_id": <int> | null,
            "ws_url":      "/api/ws/nodes/<id>" | null
        }
    """
    try:
        # Walk the workflow state records looking for any snapshot that is
        # currently SCANNING or STREAMING.
        from backend.services.workflow_state import SnapshotState
        with _workflow_state._lock:
            for ws_id, record in _workflow_state._snapshots.items():
                if record.state in (SnapshotState.SCANNING, SnapshotState.STREAMING):
                    # Double-check that the WS queue is still live.
                    if ws_id in _stream_queues:
                        return {
                            "active":      True,
                            "snapshot_id": ws_id,
                            "ws_url":      f"/api/ws/nodes/{ws_id}",
                        }
    except Exception:
        pass
    return {"active": False, "snapshot_id": None, "ws_url": None}


@router.get("/snapshot", status_code=202)
def trigger_snapshot(background_tasks: BackgroundTasks,
                     url: str = None,
                     workspace_id: str = "",
                     max_duration: int = 0):
    """
    Primary snapshot endpoint: scan → register → distill → layout → stream.

    Uses the mapper pipeline with merge-tree deduplication.
    Streams results via WebSocket at /ws/nodes/{snapshot_id} AND, via
    the workspace-id injection in ``on_stream`` below, on the long-lived
    workspace WS at /ws/workspace/{workspace_id} (§18.1 severance fix).

    ``workspace_id`` defaults to ``""`` which the WS-push helper resolves
    to ``"_default"`` so the single-workspace common case keeps working.
    """
    global SNAPSHOT_INDEX, _mapper_offset_x

    mapper = _get_mapper()

    if not url:
        if mapper.driver:
            try:
                url = mapper.driver.current_url
            except Exception:
                url = "https://example.com"
        else:
            url = "https://example.com"

    current_snapshot_id = SNAPSHOT_INDEX
    SNAPSHOT_INDEX += 1
    # §18.1 — resolve the workspace id NOW (before the background
    # closure captures it) so both the chunk stream and the scan-end
    # umap_canonical frame route to the same long-lived workspace WS.
    resolved_workspace_id = (workspace_id or "").strip() or "_default"

    # Reject overlapping snapshot requests for the same URL (debounce / race mitigation)
    ok, err_code = _workflow_state.try_begin_snapshot(current_snapshot_id, url)
    if not ok:
        raise WorkflowError(
            code=err_code,
            message="A snapshot is already in flight for this URL.",
            http_status=409,
            retryable=True,
            retry_after_ms=2000
        )

    # Prepare stream queue. Pre-create the asyncio.Queue here on the
    # event-loop thread so the WS coroutine and worker thread share the
    # same instance. The worker uses ``_ws_push(...)`` which schedules
    # ``put_nowait`` onto the loop via ``call_soon_threadsafe``.
    with _stream_lock:
        if current_snapshot_id not in _stream_queues:
            _stream_queues[current_snapshot_id] = _new_ws_queue()
        # §18.1 — pre-create the workspace queue so the on_stream
        # dual-route (snapshot + workspace) reaches a real queue even
        # if no frontend has yet opened the workspace WS. Without
        # pre-creation, chunk_added frames emitted before the
        # frontend's first workspace-WS subscription are silently
        # dropped — exactly the "severed scanning vs streaming"
        # symptom the user reported.
        ws_key = (workspace_id or "").strip() or "_default"
        if ws_key not in _workspace_queues:
            _workspace_queues[ws_key] = _new_ws_queue()

    offset = _mapper_offset_x

    def background_mapper_task(scan_url: str, snap_ws_id: int,
                               offset_x: float, ws_id: str):
        global _mapper_offset_x
        _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.SCANNING)
        try:
            print(f"\n>>>> MAPPER SCAN STARTED for {scan_url} (WS ID {snap_ws_id}) <<<<")

            def on_stream(payload):
                global _mapper_offset_x

                # §18.1 — inject workspace_id on EVERY scan-emitted payload so
                # _ws_push dual-routes to the long-lived workspace WS in
                # addition to the snapshot WS. Without this, the frontend
                # listening on /ws/workspace/<wsid> never sees chunk_added /
                # chunks_partial frames and the scan appears "severed" from the
                # workspace view. The umap_canonical frame already carries
                # workspace_id via build_umap_canonical; this extends the
                # contract to every chunk-stream frame.
                #
                # MUST precede _ws_replay.record below: record() snapshots the
                # payload (`stored_frame = dict(frame)`), so the REST replay tap
                # (/api/snapshots/<id>/replay) only captures fields present at
                # record time. Injecting after record left the SUCCESS-path
                # `done` frame in the replay buffer without workspace_id — the
                # error path sets it explicitly (so stub mode passed), so only
                # real-mode/success scans regressed (`scan-streaming-routes-to-
                # workspace-ws` failed under `all_real`).
                if isinstance(payload, dict) and 'workspace_id' not in payload:
                    payload['workspace_id'] = ws_id

                # Record to replay buffer and inject sequence number.
                seq = _ws_replay.record(str(snap_ws_id), payload)
                payload['seq'] = seq

                if payload.get('type') == 'nodes':
                    br = payload.get('boundingRadius', 50)
                    new_offset = offset_x + br * 2.5
                    if new_offset > _mapper_offset_x:
                        _mapper_offset_x = new_offset
                    node_count = len(payload.get('nodes', []))
                    # Once we have nodes, we are technically streaming layouts to the frontend
                    _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.STREAMING)
                    logger.debug("Stream pushing %d nodes to WS queue (snap %s, ws %s)",
                                 node_count, snap_ws_id, ws_id)
                _ws_push(snap_ws_id, payload)

                # W2 / §11.5 — Layout Service hook on scan-end.
                # Once the mapper signals 'done', kick the Layout
                # Service to fit UMAP over the full TF-IDF index and
                # broadcast a `umap_canonical` frame.
                #
                # USER_REQUIREMENTS_VERBATIM B.1 demanded: "Live scan
                # updates are completely broken from streaming to the
                # frontend now." The fix is twofold:
                #   1. Always log the schedule attempt + outcome so an
                #      operator can see whether the post-scan UMAP
                #      actually fires (silent-success was the prior
                #      anti-pattern that hid the severance).
                #   2. The `umap_canonical` payload carries
                #      `workspace_id` so _ws_push dual-routes to both
                #      the snapshot queue (for the live scan tab) AND
                #      the long-lived workspace queue (for any other
                #      frontend tab tracking the workspace). That dual
                #      routing was already present but conditional on
                #      the payload's workspace_id field — verified now.
                if payload.get('type') == 'done':
                    logger.info(
                        "[scan-end] firing recompute_and_broadcast for "
                        "snap=%s workspace=%r", snap_ws_id, ws_id,
                    )
                    try:
                        from backend.services.layout_service import get_layout_service
                        layout = get_layout_service(broadcast=_ws_push)

                        def _fire_umap():
                            try:
                                frame = layout.recompute_and_broadcast(
                                    snapshot_id=snap_ws_id,
                                    workspace_id=ws_id,
                                    min_docs=8,
                                )
                                if frame is None:
                                    logger.info(
                                        "[scan-end] UMAP skipped — store has "
                                        "fewer than 8 docs or filter excluded "
                                        "all chunks (snap=%s).", snap_ws_id,
                                    )
                                else:
                                    logger.info(
                                        "[scan-end] UMAP broadcast OK: snap=%s "
                                        "n_chunks=%d n_urls=%d",
                                        snap_ws_id, len(frame.coords),
                                        len(frame.url_roots),
                                    )
                            except Exception as e:
                                logger.exception(
                                    "[scan-end] UMAP recompute_and_broadcast "
                                    "raised: %s", e,
                                )

                        threading.Thread(
                            target=_fire_umap,
                            daemon=True,
                        ).start()
                    except Exception as e:
                        logger.warning("LayoutService scan-end UMAP failed to schedule: %s", e)

            # §15.10 / §9.8 duration_s time-box (Q.2): the `duration_s`
            # input port (resolved here as `max_duration`) sets the
            # scan's wall-clock bound. 0 ⇒ use the 180s default (the
            # previously hard-coded ceiling becomes the default-when-unset,
            # NOT a fixed cap). >0 ⇒ scan for that many seconds then
            # finalise; whichever of samples/duration fires first stops.
            resolved_max_duration = max_duration if (max_duration and max_duration > 0) else 180
            result = mapper.snapshot(
                url=scan_url,
                max_duration=resolved_max_duration,
                pause=0.3,
                offset_x=offset_x,
                on_stream=on_stream,
            )
            _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.COMPLETE)
            print(f">>>> MAPPER SCAN COMPLETE: {result} <<<<\n")
        except Exception as e:
            print(f"\n>>>> [CRITICAL] MAPPER SCAN ERROR <<<<")
            print(e)
            traceback.print_exc()
            print(">" * 50 + "\n")
            _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.FAILED, error_code=str(e))
            # §18.1 — error 'done' frame also carries workspace_id so
            # the long-lived workspace WS subscriber sees the failure,
            # not just the (likely-closed) snapshot WS.
            err_payload = {
                "type": "done",
                "error": str(e),
                "workspace_id": ws_id,
            }
            # Record to replay buffer so /api/snapshots/<id>/replay
            # surfaces the error done frame even if no WS was
            # subscribed at error time (and so the env-scenario can
            # assert workspace_id-injection without flaky WS timing).
            seq = _ws_replay.record(str(snap_ws_id), err_payload)
            err_payload['seq'] = seq
            _ws_push(snap_ws_id, err_payload)

    background_tasks.add_task(background_mapper_task, url, current_snapshot_id,
                              offset, resolved_workspace_id)

    return {
        "status": "accepted",
        "snapshot_ws_id": current_snapshot_id,
        "snapshot_id": current_snapshot_id,
        "ws_url": f"/api/ws/nodes/{current_snapshot_id}",
        "url": url
    }


@router.get("/map/snapshot")
def mapper_snapshot(background_tasks: BackgroundTasks, url: str = None):
    """Alias for /snapshot — backwards compatibility."""
    return trigger_snapshot(background_tasks, url=url)


@router.get("/map/urls")
def mapper_get_urls():
    """Return all URLs with registered snapshots."""
    mapper = _get_mapper()
    return {"urls": mapper.get_registered_urls()}


@router.get("/map/snapshots")
def mapper_get_snapshots(url: str):
    """Return all snapshots for a URL."""
    mapper = _get_mapper()
    return {"snapshots": mapper.get_snapshots(url)}


@router.get("/map/detail")
def mapper_node_detail(url: str, xpath: str, snapshot_id: str = None):
    """
    Get full node detail for the knowledge panel.
    Returns tag, attributes, text, HTML, label, categories, generalized xpath.
    """
    mapper = _get_mapper()
    details = mapper.get_node_detail(url, xpath, snapshot_id)
    # Forbidden-concepts (CLAUDE.md §"Graph analytics"): the graph-analytics
    # framework — `cluster_id`, `wl_hash`, and the `NodeAnalytics` table — is
    # removed. Node detail carries only DOM facts; retrieval ranks ONLY by the
    # triple product `pagerank · tfidf_cos · nomic_cos` (apparition_service).
    # (The injection here was dead anyway — nothing writes `NodeAnalytics`.)
    return details


@router.post("/map/label")
def mapper_apply_label(req: MapperLabelRequest):
    """
    Apply a user label to a node xpath.
    Commutes to all matching generalized patterns + computes LCA by default.
    """
    mapper = _get_mapper()
    result = mapper.labels.apply_label(
        req.url, req.xpath, req.label, req.snapshot_id
    )
    
    # Wrap result in the canonical Phase 14 schema
    return {
        "status": "ok",
        "instance": {"url": req.url, "xpath": req.xpath, "label": req.label},
        "commuted_xpaths": result.get("commuted_xpaths", []),
        "lca_subtree_xpaths": result.get("lca_subtree_xpaths", []),
        "lca_xpath": result.get("lca_xpath", "/"),
        "conflict": None
    }

@router.post("/map/label-batch")
def mapper_apply_label_batch(req: LabelBatchRequest):
    """Single-pass label batching for the Paint CAD tool (§14.12)."""
    # STUB: Defer to mapper label engine implementation
    return {
        "applied": [],
        "failed": [],
        "consolidated": {
            "instance_count": len(req.xpaths),
            "commuted_count": 0,
            "lca_count": 0,
            "cluster_id": "0",
            "pattern_xpaths": [],
            "lca_xpath": None
        }
    }

@router.post("/map/select-structural")
def select_structural(req: MapperLabelRequest):
    """
    Read-only preview of what an auto-commute would touch. 
    Used by the CAD "Select Similar" tool. No persistence.
    """
    general_pattern = generalize_xpath(req.xpath)
    return {"matches": [general_pattern]}  # STUB: Return actual mapped xpaths

@router.get("/map/snapshot/{snapshot_id}/content-distilled")
def get_content_distilled(snapshot_id: str):
    """Returns the distilled subtree view used by the labeling frontend (§14.4)."""
    svc = _get_content_distilled_svc()
    try:
        view = svc.view(snapshot_id)
        return dataclasses.asdict(view)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/map/labels")
def mapper_get_labels(url: str):
    """Get all labels with LCA info for a URL."""
    mapper = _get_mapper()
    return {"labels": mapper.labels.get_all_labels_with_lca(url)}


@router.post("/map/structure-tag")
def mapper_create_structure_tag(req: StructureTagRequest):
    """Create a structure tag grouping labeled instances."""
    mapper = _get_mapper()
    tag_id = mapper.labels.create_structure_tag(
        req.url, req.tag_name, req.label_group, req.description
    )
    return {"tag_id": tag_id}


@router.get("/map/structure-tags")
def mapper_get_structure_tags(url: str):
    """Get all structure tags for a URL."""
    mapper = _get_mapper()
    return {"tags": mapper.labels.get_structure_tags(url)}


# ======================================================================
# CONTENT CHUNKS (post-scan SLM-sized partitions)
# ======================================================================

class ChunkLabelRequest(BaseModel):
    chunk_id: str
    label: str
    snapshot_id: Optional[str] = None


@router.get("/map/restore")
def mapper_restore_all():
    """
    Rehydrate all persisted snapshots from Kuzu for the 3D GUI.

    Each payload mirrors a single 'nodes' WebSocket frame plus the chunks
    frame that would have followed the live scan. The frontend calls this
    on page load so previously scanned DOMs and their card panels survive
    refreshes without re-running the scanner.
    """
    mapper = _get_mapper()
    return {"snapshots": mapper.restore_all()}


@router.get("/map/snapshot/{snapshot_id}/chunks")
def mapper_get_chunks(snapshot_id: str):
    """Return the post-scan chunks for a snapshot, newest first."""
    mapper = _get_mapper()
    return {"chunks": mapper.get_chunks(snapshot_id)}


@router.post("/map/chunks/label")
def mapper_set_chunk_label(req: ChunkLabelRequest):
    """
    Manually assign (or clear) a label on a chunk.

    The SLM will eventually categorize chunks into card / nav / filter /
    paragraph etc., but users can override or pre-populate labels here.
    Labels persist to Kuzu so subsequent loads carry them through.
    """
    mapper = _get_mapper()
    ok = mapper.apply_chunk_label(req.chunk_id, req.label, req.snapshot_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update chunk label")
    return {"status": "success", "chunk_id": req.chunk_id, "label": req.label}


# ======================================================================
# DOM TEXT SEARCH + LCA + COMMUTATION (Retrieval Panel)
# ======================================================================

@router.post("/search/dom-text")
def search_dom_text(req: DomTextSearchRequest):
    """
    Substring search across all DOM nodes' text/innerHTML.

    Returns ranked results with snippet previews, node IDs, and xpaths
    for the retrieval panel. Results include both content-distilled nodes
    and raw DOM nodes — content nodes are scored higher.
    """
    mapper = _get_mapper()
    url = req.url
    if not url and mapper.driver:
        try:
            url = mapper.driver.current_url
        except Exception:
            url = ''

    if not req.query or not req.query.strip():
        return {"results": [], "query": req.query}

    results = mapper.search_dom_text(
        url=url,
        query=req.query.strip(),
        snapshot_id=req.snapshot_id,
        limit=req.limit,
    )
    return {"results": results, "query": req.query, "url": url}


@router.get("/map/lca-subtree")
def mapper_lca_subtree(url: str, label: str, snapshot_id: str = None):
    """
    Compute the LCA subtree for a label group.

    Returns the LCA xpath, all member xpaths (directly labeled),
    and all content xpaths in the connecting subtree for 3D highlighting.
    """
    mapper = _get_mapper()
    return mapper.get_lca_subtree(url, label, snapshot_id)


@router.post("/map/commutation")
def mapper_commutation_matches(req: CommutationRequest):
    """
    Find all content nodes matching the same generalized xpath pattern.

    Used for lateral commutation highlighting: given one node's xpath,
    returns all other nodes with the same structural pattern (array
    indices stripped).
    """
    mapper = _get_mapper()
    return mapper.get_commutation_matches(req.url, req.xpath, req.snapshot_id)


@router.post("/map/subgroup-commutation")
def mapper_subgroup_commutation_matches(req: CommutationRequest):
    """
    Subgroup commutation restricted to labeled LCA groups.

    Only returns matches when there are at least two labeled nodes
    whose LCA xpath is itself labeled, AND the candidate's descendant
    generalized-pattern set is identical to the source's. Produces a
    finer-grained alignment than raw pattern-equality commutation.
    """
    mapper = _get_mapper()
    return mapper.get_subgroup_commutation_matches(
        req.url, req.xpath, req.snapshot_id
    )


# ======================================================================
# CHAT MCP AND RETRIEVAL STREAM (Phase 0B, Phase 0C)
# ======================================================================

class ChatSessionRequest(BaseModel):
    title: str = "New Chat"

@router.post("/chat/session")
def create_chat_session(req: ChatSessionRequest):
    chat, _ = _get_services()
    session = chat.create_session(req.title)
    return {"session_id": session.session_id, "created_at": session.created_at}

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    chat, ret = _get_services()
    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "")
            node_context = data.get("node_context")
            
            ret.append("human", "chat_message", content, focal_node_id=node_context.get("id") if node_context else None)

            async for chunk in chat.send_message(session_id, content, node_context):
                await websocket.send_json(chunk)
                
    except WebSocketDisconnect:
        logger.info("Chat WS session %s disconnected", session_id)

class SearchHybridRequest(BaseModel):
    query: str
    mode: str = "hybrid"

@router.post("/search/hybrid")
def search_hybrid(req: SearchHybridRequest):
    _, ret = _get_services()
    entry = ret.search_human(req.query)
    return {"results": entry.data.get("results", [])}


@router.get("/session/reconcile")
def reconcile_session(url: str):
    """Return the authoritative state of every workflow for this URL (§14.8)."""
    return _workflow_state.reconcile(url)


# ======================================================================
# AGENTIC FLUID AND SCHEMA HALO (Phase 4B, 8, 9)
# ======================================================================
from backend.services.schema_introspector import SchemaIntrospector
from backend.services.open_link_resolver import OpenLinkResolver

@router.get("/graph/schema")
def get_graph_schema():
    conn = get_connection()
    introspector = SchemaIntrospector(conn)
    return introspector.build_schema_map()

@router.get("/graph/halo/{node_id}")
def get_node_halo(node_id: str, node_type: str = "OntologyNode"):
    conn = get_connection()
    embedder = None # Mock
    introspector = SchemaIntrospector(conn)
    resolver = OpenLinkResolver(conn, embedder, introspector)
    return resolver.resolve_halo(node_id, node_type, {})


class InstantiateFluidRequest(BaseModel):
    urls: List[str] = None
    custom_context: str = ""

@router.post("/agentic/instantiate")
def agentic_instantiate(req: InstantiateFluidRequest):
    chat, _ = _get_services()
    try:
        from backend.agentic.context_manager import ContextManager
        context = ContextManager().gather_context(req.urls)
        agents = chat.fluid_engine.agent_gen.generate_team(context)
        return {"fluid_id": "fluid_mock_id", "agents": [a.__dict__ for a in agents]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/agentic/propagate/{fluid_id}")
def agentic_propagate(fluid_id: str):
    return {"step_number": 1, "recommendation": "Look at the navigation elements."}

@router.post("/agentic/auto-run/{fluid_id}")
def agentic_autorun(fluid_id: str):
    return {"status": "started"}


# ======================================================================
# CHUNK PROJECTOR
# ======================================================================
# The 3D viewer (``backend/static/js/chunk_projector.js``) draws one
# sphere per ``ChunkInstance`` and per document hub. The LAYOUT AUTHORITY
# is the backend's UMAP-linear-radial fit (§2.1 / §6.1 — `LayoutService`
# + `/api/recompute_umap`, broadcast as `umap_canonical`). This topology
# endpoint ships only {id, url, is_document, doc_id} rows; the frontend
# places new chunks at a TRANSIENT hash-DIRECTION radial placeholder
# (§6.1 / §18.2 — NOT a concentric-shell / Fibonacci layout) until the
# backend's canonical UMAP coords arrive and supersede it.
#
# This replaced the prior ``ChunkUmapNode`` schema + ``_recompute_umap``
# pipeline that DROP+CREATEd a kuzu table on every chunk-count change.
# That implementation was O(N) per poll on the hottest user-visible
# request (``/api/chunk_nodes`` is called every 1.5 s during a scan);
# with layout client-side the endpoint is now a single read query and
# the projector adds new spheres in pure JS as WS frames land.


@router.get("/chunk_nodes")
def get_chunk_nodes(limit: int = 0):
    """Return one node per ``ChunkInstance`` (and one hub per URL).

    The frontend chunk projector seeds each new ``id`` at a transient
    hash-DIRECTION radial placeholder (§6.1 / §18.2), then tweens it to
    the backend's canonical UMAP coords on the next ``umap_canonical``
    frame. We only ship the topology here — no x/y/z, no r/g/b. That
    keeps the payload small and the endpoint fast even when polled by
    the GUI.

    Response::

        {
          "count": int,
          "nodes": [
            {"id", "url", "is_document", "doc_id"},
            ...
          ],
          "edges": [{"source": instance_id, "target": doc_id}, ...]
        }
    """
    conn = get_connection()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_urls: Dict[str, str] = {}

    try:
        res = conn.execute("MATCH (c:ChunkInstance) RETURN c.instance_id, c.url, c.chunk_id")
        while res.has_next():
            r = res.get_next()
            iid = r[0]
            if not iid:
                continue
            url = r[1] or ""
            chunk_id = r[2] or ""
            doc_id = seen_urls.get(url)
            if doc_id is None and url:
                doc_id = f"doc_{url}"
                seen_urls[url] = doc_id
                nodes.append({
                    "id": doc_id, "url": url,
                    "is_document": True, "doc_id": "",
                })
            nodes.append({
                "id": iid, "url": url,
                "is_document": False, "doc_id": doc_id or "",
                "chunk_id": chunk_id,
            })
            if doc_id:
                edges.append({"source": iid, "target": doc_id})
    except Exception as e:
        logger.warning("chunk_nodes ChunkInstance query failed: %s", e)
        return {"count": 0, "nodes": [], "edges": []}

    if limit and limit > 0:
        nodes = nodes[:limit]
    return {"count": len(nodes), "nodes": nodes, "edges": edges}


@router.post("/recompute_umap")
def recompute_umap(min_docs: int = 8):
    """Compute a 3D semantic projection of every chunk in the TF-IDF store.

    Returns a mapping {chunk_id: [x, y, z]} so the frontend can stream
    coordinate updates onto the existing 3D scene without re-loading
    every node. Used by the incremental-UMAP scheduler that fires when
    the chunk count crosses 500 (then doubles) — see scanner.js
    ``_maybeRecomputeUmap``.

    Implementation: the canonical neighbour-preserving 6D embedding
    (real UMAP via ``LayoutService._embed_6d``, degrading loudly to
    TruncatedSVD per §6.1 / §B.2 / §13.4) against the live TF matrix.
    TF-IDF is row-l2-normalised first so frequent-vocab chunks don't
    dominate the projection. Output position coords are centred at the
    origin and rescaled so they live in the same neighbourhood as the
    hash-based bootstrap layout (DOC_SHELL_RADIUS = 40 in cp/layout.js).

    If the store has fewer than ``min_docs`` chunks we skip the projection
    entirely (small matrices give noisy embeddings); the frontend falls
    back to its hash-radial layout.
    """
    import numpy as np
    from scipy import sparse as sp
    from sklearn.decomposition import TruncatedSVD
    try:
        from sklearn.preprocessing import normalize
    except Exception:
        normalize = None
    # Lazy import — the route is rarely called and the store module
    # touches numpy/scipy at import time. The sibling /api/search route
    # below uses the same pattern; keep them consistent.
    from backend.services.global_tfidf_store import get_default_store
    from backend.services.layout_service import get_layout_service

    store = get_default_store()
    n_docs = store.doc_count
    chunk_ids = list(store._chunk_ids)
    if n_docs < int(min_docs) or n_docs == 0:
        return {
            "status": "skipped",
            "reason": f"only {n_docs} chunks in store (need ≥ {min_docs})",
            "doc_count": n_docs,
            "coords": {},
        }

    tf = store._tf
    if tf is None or tf.shape[0] != n_docs or tf.shape[1] == 0:
        return {
            "status": "skipped",
            "reason": "TF matrix missing or shape mismatch",
            "doc_count": n_docs,
            "coords": {},
        }

    # Row-normalise so high-frequency vocab doesn't swamp the projection.
    X = tf.astype(np.float32)
    if normalize is not None:
        X = normalize(X, norm="l2", axis=1, copy=False)
    else:
        # Manual L2 normalisation on CSR rows.
        sq = X.multiply(X).sum(axis=1)
        norms = np.sqrt(np.asarray(sq).ravel()).clip(min=1e-9)
        X = sp.diags(1.0 / norms) @ X

    # §6.1 / §B.2 — use the canonical neighbour-preserving embedding
    # (real UMAP, loud SVD fallback) shared with LayoutService so the
    # manual/incremental recompute matches the scan-end fit exactly,
    # rather than this route's old inline TruncatedSVD (which scrambled
    # the cosine neighbourhood UMAP preserves).
    _ls = get_layout_service(broadcast=_ws_push)
    Y = _ls._embed_6d(X, X.shape[0])
    if Y is None:
        return {
            "status": "skipped",
            "reason": "matrix too small for projection",
            "doc_count": n_docs,
            "coords": {},
        }
    # Pad to 6 columns if vocab is tiny — 3 position + 3 HSV.
    if Y.shape[1] < 6:
        pad = np.zeros((Y.shape[0], 6 - Y.shape[1]), dtype=Y.dtype)
        Y = np.hstack([Y, pad])

    # Centre and rescale POSITION channels to ~80-unit cube; HSV
    # normalises to [0, 1] independently per channel.
    pos = Y[:, :3]
    pos = pos - pos.mean(axis=0, keepdims=True)
    span = float(np.max(np.abs(pos)))
    if span < 1e-9:
        span = 1.0
    pos = pos * (40.0 / span)
    hsv = Y[:, 3:6].copy()
    for j in range(hsv.shape[1]):
        col = hsv[:, j]
        lo, hi = float(col.min()), float(col.max())
        rng = hi - lo
        if rng < 1e-9:
            hsv[:, j] = 0.5
        else:
            hsv[:, j] = (col - lo) / rng

    coords = {}
    for i, cid in enumerate(chunk_ids):
        coords[cid] = [
            float(pos[i, 0]), float(pos[i, 1]), float(pos[i, 2]),
            float(hsv[i, 0]) if hsv.shape[1] > 0 else 0.5,
            float(hsv[i, 1]) if hsv.shape[1] > 1 else 0.5,
            float(hsv[i, 2]) if hsv.shape[1] > 2 else 0.5,
        ]

    # W2 / §11.5 — Broadcast umap_canonical to any active WS so
    # listeners get the same coords through the canonical frame
    # vocabulary. The REST response keeps the legacy ``coords`` field
    # for direct callers (older frontend code path).
    try:
        from backend.services.layout_service import get_layout_service
        layout = get_layout_service(broadcast=_ws_push)
        # The manual recompute can run with no scan-in-flight; fire
        # the full pipeline (per-URL + collider) so the broadcast
        # carries url_roots + post-processed coords, not just the raw
        # SVD output we computed inline above.
        frame = layout.recompute(min_docs=min_docs, workspace_id="")
        if frame is not None:
            payload = build_umap_canonical(
                workspace_id=frame.workspace_id or "_default",
                coords=frame.coords,
                url_roots=frame.url_roots,
                provenance=frame.provenance,
            )
            # Broadcast to every currently-subscribed snapshot WS.
            for sid in list(_stream_queues.keys()):
                _ws_push(sid, payload)
            coords = frame.coords  # Prefer post-processed coords in REST resp
    except Exception as e:
        logger.warning("LayoutService manual recompute broadcast failed: %s", e)

    return {
        "status": "success",
        "doc_count": n_docs,
        # 6D contract (§1.8): 3 position + 3 HSV. (The old inline-SVD
        # code's `n_comp` local was removed in the G2 real-UMAP swap but
        # this response still referenced it — a NameError that 500'd the
        # route AFTER computing coords; found by the §16.5 probe.)
        "n_components": 6,
        "coords": coords,
    }


def invalidate_chunk_nodes_cache() -> None:
    """Compatibility no-op.

    The pipeline persist worker used to call this to bust the
    server-side fingerprint cache. With layout client-side there is
    no cache to bust — the projector just reads ``/api/chunk_nodes``
    when it needs a refresh. Kept callable so existing pipeline
    code doesn't crash on import.
    """
    return


@router.get("/chunk_details/{instance_id}")
def get_chunk_details(instance_id: str):
    """Full row for one chunk instance -- used when the billboard opens.

    Tries the live delta state first (available during an active scan
    before DB persistence) then falls back to the persisted DB row.
    """
    import json as _json
    # §U — derived, additive deduplicated content tree (the black-slate HTML
    # chunk card body). Computed from the existing `fields` extraction; never
    # alters chunk bookkeeping (V.1).
    from backend.dom.content_tree import fields_to_content_tree

    # Live delta path (§8.4): read from in-memory master tree
    mapper = _get_mapper()
    live = mapper.get_live_chunk_detail(instance_id)
    if live is not None:
        return {
            "id": instance_id,
            "chunk_id": live["chunk_id"],
            "html_raw": live["html_raw"],
            "rendered_text": live["rendered_text"],
            "image_urls": live["image_urls"],
            "content_fields": live["content_fields"],
            "fields": live["content_fields"],
            "content_tree": fields_to_content_tree(live["content_fields"]),
        }

    # DB fallback
    from backend.services.chunk_instance_persistence import load_instance_by_id
    conn = get_connection()
    row = load_instance_by_id(conn, instance_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No instance {instance_id!r}")
    try:
        fields = _json.loads(row.fields_json) if row.fields_json else {}
    except Exception:
        fields = {}
    return {
        "id": row.instance_id,
        "chunk_id": row.chunk_id,
        "pattern_id": row.pattern_id,
        "url": row.url,
        "absolute_xpath": row.absolute_xpath,
        "html_raw": row.html_raw,
        "rendered_text": row.rendered_text,
        "fields": fields,
        "fields_json": row.fields_json,
        "created_at": row.created_at,
        "content_tree": fields_to_content_tree(fields),
    }


@router.post("/chunk_details_batch")
def get_chunk_details_batch(instance_ids: List[str] = Body(...)):
    """Batch fetch details for a list of instance IDs, streaming as NDJSON."""
    import json as _json
    from backend.services.chunk_instance_persistence import load_instances_by_ids
    from backend.dom.content_tree import fields_to_content_tree
    conn = get_connection()
    rows = load_instances_by_ids(conn, instance_ids)

    def ndjson_generator():
        for row in rows:
            try:
                fields = _json.loads(row.fields_json) if row.fields_json else {}
            except Exception:
                fields = {}

            out = {
                "id": row.instance_id,
                "chunk_id": row.chunk_id,
                "pattern_id": row.pattern_id,
                "url": row.url,
                "absolute_xpath": row.absolute_xpath,
                "html_raw": row.html_raw,
                "rendered_text": row.rendered_text,
                "fields": fields,
                "fields_json": row.fields_json,
                "created_at": row.created_at,
                "content_tree": fields_to_content_tree(fields),
            }
            yield _json.dumps(out) + "\n"
            
    return StreamingResponse(ndjson_generator(), media_type="application/x-ndjson")


class ChunkSearchRequest(BaseModel):
    """NL search over the full chunk corpus."""
    query: str
    urls: Optional[List[str]] = None
    page_limit: int = 5
    instance_limit_per_page: int = 5


@router.post("/chunk_search")
def chunk_search(req: ChunkSearchRequest):
    """TF-IDF retrieval against the GLOBAL incremental store.

    The store accumulates every chunk from every scan into one
    ever-growing sparse matrix with a monotonic vocabulary. A query
    becomes one sparse matvec — no per-call DB scan, no per-snapshot
    .npz file management. The mapper updates the store at the end
    of each scan (raw TF row appended/replaced; df bumped; IDF
    recomputed lazily at query time).

    Response::

        {
          "query": str,
          "pages": [
             {"url", "score", "instance_count",
              "instances": [
                 {"id","url","absolute_xpath","html_raw",
                  "rendered_text","score"},
                 ...
              ]
             },
             ...
          ]
        }
    """
    import json as _json
    from collections import defaultdict
    from backend.services.global_tfidf_store import get_default_store

    if not req.query.strip():
        return {"query": req.query, "pages": []}

    def _safe_fields(fj: str) -> Dict[str, Any]:
        if not fj:
            return {}
        try:
            return _json.loads(fj)
        except Exception:
            return {}

    store = get_default_store()
    if store.doc_count == 0:
        return {"query": req.query, "pages": []}

    # Pull a generous top-K from the global store so we have enough
    # rows to group by URL afterwards. ``page_limit *
    # instance_limit_per_page * 4`` covers cases where one URL
    # dominates the head of the result list.
    overshoot = max(40, req.page_limit * req.instance_limit_per_page * 4)
    hits = store.search(req.query, k=overshoot, urls=req.urls)
    if not hits:
        return {"query": req.query, "pages": []}

    # Group by URL; aggregate page score as sum-of-top-K instance
    # scores so a multi-relevant page beats a one-shot match.
    by_url: Dict[str, List] = defaultdict(list)
    for h in hits:
        by_url[h.meta.url].append(h)

    page_top_k = max(1, req.instance_limit_per_page)
    page_scores: List[Tuple[str, float, List]] = []
    for u, hs in by_url.items():
        hs.sort(key=lambda h: -h.score)
        top = hs[:page_top_k]
        # Page score is the MEAN of top-K instance cosines, not the
        # sum — sum-of-top-K let the page score climb past 1.0 (the
        # user reported "600 %" in the GUI, which was 6.0 from
        # 6 instances each ~1.0). Mean keeps the page score on the
        # same [0, 1] scale as instance cosines, so the frontend
        # "X %" formatting reads correctly.
        page_score = float(sum(h.score for h in top) / len(top)) if top else 0.0
        if page_score > 0:
            page_scores.append((u, page_score, top))
    page_scores.sort(key=lambda t: -t[1])
    page_scores = page_scores[: max(1, req.page_limit)]

    # The store keeps lightweight metadata; for the response we
    # also want html_raw + fields_json so the GUI can render the
    # billboard preview without an extra round-trip. Pull those
    # from kuzu in one batched fetch.
    needed_ids = [h.meta.chunk_id for _, _, top in page_scores for h in top]
    extras: Dict[str, Tuple[str, str, str]] = {}
    if needed_ids:
        conn = get_connection()
        for cid in needed_ids:
            try:
                res = conn.execute(
                    "MATCH (c:ChunkInstance {instance_id: $iid}) "
                    "RETURN c.absolute_xpath, c.html_raw, c.fields_json LIMIT 1",
                    parameters={"iid": cid},
                )
                if res.has_next():
                    r = res.get_next()
                    extras[cid] = (r[0] or "", r[1] or "", r[2] or "")
            except Exception:
                pass

    pages_out: List[Dict[str, Any]] = []
    for u, score, top in page_scores:
        pages_out.append({
            "url": u,
            "score": score,
            "instance_count": len(by_url[u]),
            "instances": [
                {
                    "id": h.meta.chunk_id,
                    "url": u,
                    "absolute_xpath": (
                        extras.get(h.meta.chunk_id, ("", "", ""))[0]
                        or h.meta.absolute_xpath
                    ),
                    "html_raw": extras.get(h.meta.chunk_id, ("", "", ""))[1],
                    "rendered_text": h.meta.text_preview,
                    "fields": _safe_fields(extras.get(h.meta.chunk_id, ("", "", ""))[2]),
                    "score": float(h.score),
                }
                for h in top
            ],
        })
    return {"query": req.query, "pages": pages_out}


# ---------------------------------------------------------------------------
# Image proxy — required for WebGL sphere replacement across origins
# ---------------------------------------------------------------------------
#
# three.js ``TextureLoader`` uploads images to a WebGL texture, and WebGL
# refuses to sample cross-origin images unless the response carries
# ``Access-Control-Allow-Origin``. Most source sites don't serve CORS on
# their assets, so ``<img>`` tags inside the right-hand billboard panel
# display fine (no CORS needed for display, only for canvas/GL readback)
# but sphere replacement silently fails. This endpoint re-serves the image
# bytes with ``Access-Control-Allow-Origin: *`` so the texture upload
# succeeds.
#
# Security:
# * Only http/https URLs are honoured.
# * A 10s timeout + 20MB cap prevents the proxy from being abused as a
#   general-purpose data mover.
# * We do not follow redirects to non-http(s) schemes (httpx default).
# * The response streams straight through — we never write to disk.

_IMAGE_PROXY_TIMEOUT = 10.0
_IMAGE_PROXY_MAX_BYTES = 20 * 1024 * 1024  # 20 MB hard cap
# Accept common image and video mime prefixes (videos are fine for
# three.js VideoTexture usage even though the current sphere-replacement
# path only hands ``image/*`` to TextureLoader).
_IMAGE_PROXY_ALLOWED_PREFIXES = ("image/", "video/")


@router.get("/image_proxy")
async def image_proxy(url: str):
    """CORS-enabled pass-through fetch for third-party image URLs.

    The frontend routes sphere-replacement textures through this endpoint
    so WebGL can sample them regardless of the source origin's CORS
    policy. Used ONLY for 3D canvas textures; the billboard panel
    continues to use direct ``<img>`` tags (no CORS needed for display).

    Hardening notes (the user kept seeing 502s on ``archive.org`` image
    fetches that succeed in a normal browser):

      * The request now carries a per-host ``Referer`` header derived
        from the URL itself. Several CDNs (archive.org, wikimedia,
        substack media) gate image delivery on a same-origin referer
        and return 403 / 502 without it.
      * Connection / timeout errors are retried once with a 250 ms
        sleep — most upstream blips clear inside that window.
      * Distinct upstream statuses map to distinct proxy statuses:
        4xx → mirrored 4xx (404 stays 404), 5xx / network → 502 so the
        frontend's per-host failure counter only counts real outages.
      * If everything fails, the proxy emits a tiny 1×1 transparent
        PNG with ``Cache-Control: max-age=60`` so the WebGL texture
        loader still resolves and the user doesn't see a black hole
        where the sprite was meant to be.
    """
    if not isinstance(url, str) or not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    raw = url.strip()
    low = raw.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        raise HTTPException(status_code=400, detail="Only http(s) URLs are allowed")

    try:
        import httpx  # local import keeps module-level import graph small
        from fastapi.responses import Response
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"image_proxy dependencies missing: {e}")

    # Derive a believable Referer from the URL's own host. archive.org
    # specifically rejects the bare User-Agent + Accept combination
    # with a 5xx burst when no Referer is present; setting it to
    # ``https://<host>/`` is what every browser does by default for
    # cross-origin image loads.
    from urllib.parse import urlsplit
    try:
        parts = urlsplit(raw)
        host = parts.netloc
        referer = f"{parts.scheme}://{host}/" if host else None
    except Exception:
        referer = None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,video/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }
    if referer:
        headers["Referer"] = referer

    import asyncio
    resp = None
    last_err: Exception | None = None
    for attempt in range(2):  # original + one retry
        try:
            async with httpx.AsyncClient(
                timeout=_IMAGE_PROXY_TIMEOUT,
                follow_redirects=True,
                headers=headers,
            ) as client:
                resp = await client.get(raw)
            break
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            last_err = e
            if attempt == 0:
                await asyncio.sleep(0.25)
                continue
            resp = None
            break
        except httpx.HTTPError as e:
            last_err = e
            resp = None
            break

    if resp is None:
        # Connection-level failure after one retry. Return the
        # transparent-pixel fallback so WebGL's image-load promise
        # still settles and the per-host failure counter stays clean.
        return _empty_image_response(detail=f"upstream unreachable: {last_err}")

    if resp.status_code >= 400:
        # Mirror 4xx semantics; collapse 5xx to 502 so the frontend
        # treats them as transient.
        if 400 <= resp.status_code < 500:
            return _empty_image_response(
                detail=f"upstream {resp.status_code}",
                cache_seconds=300,  # client-side dedup so we stop re-asking
            )
        return _empty_image_response(
            detail=f"upstream {resp.status_code}",
            cache_seconds=15,
        )

    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if not any(ctype.startswith(p) for p in _IMAGE_PROXY_ALLOWED_PREFIXES):
        # Some servers don't label content-type at all but the URL suggests
        # an image. Accept in that case too — WebGL will reject non-image
        # bytes on upload which is the next line of defense.
        if ctype:
            return _empty_image_response(
                detail=f"upstream content-type {ctype!r} not a supported media type",
                cache_seconds=300,
            )
        ctype = "application/octet-stream"

    body = resp.content
    if len(body) > _IMAGE_PROXY_MAX_BYTES:
        return _empty_image_response(
            detail="upstream asset too large",
            cache_seconds=300,
        )

    return Response(
        content=body,
        media_type=ctype,
        headers={
            "Access-Control-Allow-Origin": "*",
            # Let the browser cache proxied textures — they're immutable
            # per-URL. 1 hour is enough to cover a typical session without
            # pinning stale assets forever.
            "Cache-Control": "public, max-age=3600",
        },
    )


# 1×1 transparent PNG (67 bytes). Returned by the proxy on any
# unrecoverable upstream error so the WebGL TextureLoader promise
# resolves cleanly and the frontend's per-host failure counter only
# ticks for genuine outages.
_EMPTY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
    b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc"
    b"\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _empty_image_response(*, detail: str = "", cache_seconds: int = 60):
    """Return a 200 response with a transparent 1×1 PNG so the
    frontend's image-load path still resolves on upstream failure.

    The detail string is surfaced via a custom ``X-Image-Proxy-Note``
    header so callers (and the browser's network panel) can still see
    what happened upstream without us having to throw an HTTPException.
    """
    from fastapi.responses import Response
    return Response(
        content=_EMPTY_PNG,
        media_type="image/png",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": f"public, max-age={int(cache_seconds)}",
            "X-Image-Proxy-Note": detail[:200] if detail else "empty",
        },
    )


# ---------------------------------------------------------------------------
# W4 / §8D.44 — Concept node + edge REST endpoints
#
# Backend persistence layer for the 2D concept editor (cp/concept_graph.js).
# Wire-shaped Pydantic models keep the API contract stable while the
# graph_editor.py implementation handles both Kuzu write-through and the
# in-memory fallback. Workspace scoping is by ``workspace_id`` query param
# (defaults to empty string for unscoped concepts).
# ---------------------------------------------------------------------------

class ConceptNodeRequest(BaseModel):
    """Request body for create/update concept node operations.

    ``idempotency_key`` (optional) — client-supplied UUID per logical
    edit. The backend caches the response by (workspace_id, concept_id,
    key) over ``settings.idempotency_ttl_sec``; a retry hits the cache
    and returns the prior result without re-firing the lifecycle. This
    prevents duplicate broadcasts + evolution-log entries when the
    network forces the client to retry a PATCH/POST. Clients that
    don't care about retry safety can omit the key.
    """
    concept_id: Optional[str] = None
    name: str = ""
    description: str = ""
    data: str = ""
    rendering: str = ""
    backing_pointer: str = ""
    provenance: str = "user-authored"
    workspace_id: str = ""
    layout_xy: Optional[Dict[str, float]] = None
    ui_state: Optional[Dict[str, Any]] = None
    type_hint: str = ""
    idempotency_key: Optional[str] = None


class ConceptEdgeRequest(BaseModel):
    source_id: str
    target_id: str
    edge_type: str = "RELATES_TO"
    source_port: str = ""
    target_port: str = ""
    weight: Optional[float] = None
    variable_name: str = ""
    workspace_id: str = ""
    idempotency_key: Optional[str] = None
    # Phase 7 EXPLORE-03 / N.4 — see EditorLinkRequest.inherit_types docstring
    # for the full contract; same semantics, same default-False safety.
    inherit_types: bool = False


_graph_editor_singleton = None


def _get_graph_editor():
    """Lazy-init the GraphEditor singleton bound to the live DB connection.

    Delegates to ``backend.services.graph_editor.get_default_graph_editor``
    so cascade ticks, backing-registry resolvers, and signal pipelines
    all share one instance + its in-memory caches.
    """
    from backend.services.graph_editor import get_default_graph_editor
    return get_default_graph_editor()


def _concept_to_dict(node) -> Dict[str, Any]:
    """Serialise a ConceptNode dataclass into the wire payload."""
    if node is None:
        return {}
    return {
        "concept_id": node.concept_id,
        "name": node.name,
        "description": node.description,
        "data": node.data,
        "rendering": node.rendering,
        "linked_nodes_json": node.linked_nodes_json,
        "backing_pointer": node.backing_pointer,
        "pagerank": float(node.pagerank or 0.0),
        "provenance": node.provenance,
        "workspace_id": node.workspace_id,
        "layout_xy": node.layout_xy,
        "ui_state": node.ui_state,
        "type_hint": node.type_hint,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


def _edge_to_dict(edge) -> Dict[str, Any]:
    if edge is None:
        return {}
    return {
        "edge_id": edge.edge_id,
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "edge_type": edge.edge_type,
        "source_port": edge.source_port,
        "target_port": edge.target_port,
        "weight": edge.weight,
        "variable_name": edge.variable_name,
        "workspace_id": edge.workspace_id,
        "created_at": edge.created_at,
    }


# ---------------------------------------------------------------------------
# Concept-mutation lifecycle hooks live in ``concept_lifecycle.py`` so
# both REST handlers and the agent's ActionResolver run the same chain
# (broadcast + index + projection + evolution log). Bind ``_ws_push``
# here so callers don't have to repeat themselves.
# ---------------------------------------------------------------------------


def _apply_create_lifecycle(node, ge, *, node_dict=None, actor: str = "user:_anon"):
    from backend.services.concept_lifecycle import apply_create_lifecycle
    return apply_create_lifecycle(
        node, ge, push_fn=_ws_push, node_dict=node_dict, actor=actor,
    )


def _apply_update_lifecycle(
    node, ge, *, pre_dict, embed_fields_changed=None,
    node_dict=None, actor: str = "user:_anon",
):
    """Thin wrapper that binds ``_ws_push`` and delegates to the
    lifecycle module. ``embed_fields_changed`` defaults to ``None``
    so the helper auto-detects changes from the pre/post diff —
    callers that have explicit knowledge can still pin it.
    """
    from backend.services.concept_lifecycle import apply_update_lifecycle
    return apply_update_lifecycle(
        node, ge, pre_dict=pre_dict,
        embed_fields_changed=embed_fields_changed,
        push_fn=_ws_push, node_dict=node_dict, actor=actor,
    )


def _apply_delete_lifecycle(concept_id: str, pre_dict, ge, *, actor: str = "user:_anon") -> None:
    from backend.services.concept_lifecycle import apply_delete_lifecycle
    apply_delete_lifecycle(concept_id, pre_dict, ge, push_fn=_ws_push, actor=actor)


def _schedule_output_projection(workspace_id: str, ge) -> None:
    from backend.services.concept_lifecycle import schedule_output_projection
    schedule_output_projection(workspace_id, ge, push_fn=_ws_push)


@router.get("/concepts")
def list_concepts(
    workspace_id: Optional[str] = None,
    type_hint: Optional[str] = None,
    provenance: Optional[str] = None,
    limit: int = 1000,
):
    """List ConceptNodes optionally filtered by workspace / type / provenance.

    Returns ``{ concepts: [{...}, ...], edges: [{...}, ...] }`` so the
    frontend can hydrate the editor's in-memory map + edge list on
    workspace open.
    """
    ge = _get_graph_editor()
    nodes = ge.list_concepts(
        workspace_id=workspace_id,
        type_hint=type_hint,
        provenance=provenance,
        limit=limit,
    )
    edges = ge.list_concept_edges(workspace_id=workspace_id, limit=int(limit) * 5)
    return {
        "concepts": [_concept_to_dict(n) for n in nodes],
        "edges": [_edge_to_dict(e) for e in edges],
    }


@router.post("/concepts")
async def create_concept(req: ConceptNodeRequest):
    """Create a new ConceptNode. Idempotent on ``concept_id`` collision.

    Also dedupes by ``idempotency_key`` over ``settings.idempotency_ttl_sec``
    so a retry doesn't fire duplicate broadcasts + log entries.

    Async — the create + lifecycle dispatch (which can trigger nomic
    embedder load on first call) runs in an executor so the event
    loop stays responsive for concurrent REST + WS traffic.
    """
    cached = _idempotency_lookup(req.workspace_id, req.concept_id or "", req.idempotency_key)
    if cached is not None:
        return cached
    ge = _get_graph_editor()

    def _create_blocking() -> Dict[str, Any]:
        node = ge.create_concept(
            name=req.name,
            description=req.description,
            data=req.data,
            rendering=req.rendering,
            backing_pointer=req.backing_pointer,
            provenance=req.provenance,
            workspace_id=req.workspace_id,
            layout_xy=req.layout_xy,
            ui_state=req.ui_state,
            type_hint=req.type_hint,
            concept_id=req.concept_id,
        )
        node_dict = _concept_to_dict(node)
        refreshed = _apply_create_lifecycle(node, ge, node_dict=node_dict)
        return (refreshed or node_dict, node.concept_id if node else (req.concept_id or ""))

    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()
    response, cid = await loop.run_in_executor(None, _create_blocking)
    # Store under BOTH the request's concept_id (which may be empty if
    # the client let the server pick) AND the resolved id. Without the
    # first store, the second POST with the same idempotency_key but
    # an empty client-side concept_id would miss the cache (it looks
    # up with "" but the first call stored under the generated UUID).
    _idempotency_store(req.workspace_id, req.concept_id or "", req.idempotency_key, response)
    if cid and cid != (req.concept_id or ""):
        _idempotency_store(req.workspace_id, cid, req.idempotency_key, response)
    return response


# ---------------------------------------------------------------------------
# W36 (early) — Concept graph export / import
#
# These static-path routes MUST come before ``/concepts/{concept_id}`` so the
# parametric route doesn't swallow ``/export`` and ``/import`` as a literal
# concept id (which 404s with "ConceptNode export not found"). The W36 block
# further down only holds a pointer to this location.
# ---------------------------------------------------------------------------

@router.get("/concepts/export")
def export_concept_graph(workspace_id: str = ""):
    """Export the workspace's concept graph as a portable JSON bundle.

    The bundle contains every concept node + every edge + the
    evolution-log diff stream (for full provenance preservation).
    Importable via ``POST /api/concepts/import`` into the same or
    a different workspace.
    """
    try:
        ge = _get_graph_editor()
        nodes = ge.list_concepts(workspace_id=workspace_id, limit=10000)
        edges = ge.list_concept_edges(workspace_id=workspace_id, limit=50000)
        log_entries: List[Dict[str, Any]] = []
        try:
            from backend.services.evolution_log import get_evolution_log
            log_entries = [
                d.to_dict() for d in get_evolution_log(graph_editor=ge).list_diffs(
                    workspace_id=workspace_id, limit=10000,
                )
            ]
        except Exception:
            pass
        return {
            "schema_version": 1,
            "workspace_id": workspace_id,
            "exported_at": __import__("time").time(),
            "concepts": [_concept_to_dict(n) for n in nodes],
            "edges": [_edge_to_dict(e) for e in edges],
            "evolution_log": log_entries,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


class ConceptImportRequest(BaseModel):
    bundle: Dict[str, Any]
    target_workspace_id: str = ""
    merge: bool = True   # if False, wipe target workspace first


@router.post("/concepts/import")
def import_concept_graph(req: ConceptImportRequest):
    """Import a previously-exported concept graph bundle.

    With ``merge=False``, all existing concepts in
    ``target_workspace_id`` are deleted first; with ``merge=True``
    the import is additive (existing concepts with the same id are
    skipped via idempotent create).
    """
    try:
        ge = _get_graph_editor()
        target_ws = req.target_workspace_id or ""
        if not req.merge:
            # Wipe existing concepts in the target workspace.
            existing = ge.list_concepts(workspace_id=target_ws, limit=10000)
            for n in existing:
                try:
                    ge.delete_concept(n.concept_id)
                except Exception:
                    pass
        imported_concepts = 0
        imported_edges = 0
        for c in (req.bundle.get("concepts") or []):
            try:
                ge.create_concept(
                    concept_id=c.get("concept_id"),
                    name=c.get("name", ""),
                    description=c.get("description", ""),
                    data=c.get("data", ""),
                    rendering=c.get("rendering", ""),
                    backing_pointer=c.get("backing_pointer", ""),
                    provenance=c.get("provenance", "user-authored"),
                    workspace_id=target_ws,
                    type_hint=c.get("type_hint", ""),
                )
                imported_concepts += 1
            except Exception:
                continue
        for e in (req.bundle.get("edges") or []):
            try:
                ge.create_concept_edge(
                    source_id=e.get("source_id", ""),
                    target_id=e.get("target_id", ""),
                    edge_type=e.get("edge_type", "RELATES_TO"),
                    source_port=e.get("source_port", ""),
                    target_port=e.get("target_port", ""),
                    weight=e.get("weight"),
                    variable_name=e.get("variable_name", ""),
                    workspace_id=target_ws,
                )
                imported_edges += 1
            except Exception:
                continue
        return {
            "ok": True,
            "imported_concepts": imported_concepts,
            "imported_edges": imported_edges,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Phase 7 (EXPLORE-01 / D-03) — rank-1 next-rank type-graph fetch.
#
# Static-path route, registered ABOVE the parametric ``/concepts/{concept_id}``
# route below (same ordering hazard the W36 NOTE above describes) so
# ``next_rank`` is never swallowed as a literal concept id.
# ---------------------------------------------------------------------------

# The ONLY edge vocabulary the materialiser writes for the python-native
# Object/Property/Function type graph (python_api_materialiser.py lines
# 19-22). next_rank must filter to exactly these four — never a parallel
# vocabulary (D10 / D-03).
_NEXT_RANK_EDGE_TYPES = {
    "OBJECT_HAS_PROPERTY",
    "OBJECT_HAS_FUNCTION",
    "FUNCTION_INPUT_TYPE",
    "FUNCTION_OUTPUT_TYPE",
}

# Render-hint per edge_type — purely a frontend rendering label; carries no
# new computation (the frontend renders, never computes, per D10).
_NEXT_RANK_RELATION_HINT = {
    "OBJECT_HAS_PROPERTY": "property",
    "OBJECT_HAS_FUNCTION": "function",
    "FUNCTION_INPUT_TYPE": "input_type",
    "FUNCTION_OUTPUT_TYPE": "output_type",
}


def _inherit_io_types(ge, source_id: str, target_id: str, workspace_id: str) -> List[Any]:
    """Phase 7 EXPLORE-03 / N.4 — copy ``source_id``'s rank-1 I/O types +
    object model onto ``target_id``.

    Reads the SAME four-edge materialiser vocabulary ``next_rank`` reads
    (``_NEXT_RANK_EDGE_TYPES`` — never a parallel vocabulary, per D10/D-03)
    via ``list_concept_edges(source_id=...)``, and for each one creates an
    equivalent edge rooted at ``target_id`` pointing at the SAME typed
    neighbor node (an inheritance mirror, not a duplicate subtree). Returns
    the list of newly-created ``ConceptEdge`` objects so the caller can fan
    each one through ``apply_edge_create_lifecycle`` (one synchronous
    side-effect inside the same request, RESEARCH Open-Q3).

    Self-referential-safe: skips any source edge whose target_id equals
    source_id (mirrors next_rank's own T-07-01 DoS guard) and never walks
    beyond rank-1 — it only reads ``source_id``'s own outgoing edges.
    """
    inherited: List[Any] = []
    source_edges = ge.list_concept_edges(workspace_id=workspace_id, source_id=source_id)
    for edge in source_edges:
        if edge.edge_type not in _NEXT_RANK_EDGE_TYPES:
            continue
        if edge.target_id == source_id:
            continue
        new_edge = ge.create_concept_edge(
            source_id=target_id,
            target_id=edge.target_id,
            edge_type=edge.edge_type,
            workspace_id=workspace_id,
        )
        inherited.append(new_edge)
    return inherited


@router.get("/concepts/{concept_id}/next_rank")
def get_concept_next_rank(concept_id: str, workspace_id: str = ""):
    """EXPLORE-01 / D-03 — rank-1 typed neighbors of a python-native node.

    Reads the materialiser's already-written ``OBJECT_HAS_PROPERTY`` /
    ``OBJECT_HAS_FUNCTION`` / ``FUNCTION_INPUT_TYPE`` / ``FUNCTION_OUTPUT_TYPE``
    edges (backend/services/python_api_materialiser.py) and shapes them into a
    rank-1 typed-neighbor list for the frontend's hover/right-click next-rank
    expansion. This route only reads + shapes graph data already written by
    the materialiser — it does NOT compute or infer any new type information
    (D10: type-graph computation stays backend, but this is no more than the
    existing edges shaped for rendering; no new type DERIVATION is added).

    Rank-1 ONLY: never walks beyond the node's direct out-edges (DoS
    mitigation, T-07-01), and skips any self-referential edge (an edge whose
    target_id equals concept_id) so a cyclic materialised graph can't loop
    the caller back onto the same node it asked about.
    """
    ge = _get_graph_editor()
    node = ge.get_concept(concept_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"ConceptNode {concept_id} not found")

    edges = ge.list_concept_edges(workspace_id=workspace_id, limit=50000)
    neighbors: List[Dict[str, Any]] = []
    for edge in edges:
        if edge.source_id != concept_id:
            continue
        if edge.edge_type not in _NEXT_RANK_EDGE_TYPES:
            continue
        if edge.target_id == concept_id:
            # Self-referential edge — rank-1 only, never fold back onto self.
            continue
        target = ge.get_concept(edge.target_id)
        if target is None:
            continue
        neighbors.append({
            "concept_id": target.concept_id,
            "name": target.name,
            "type_hint": target.type_hint,
            "edge_type": edge.edge_type,
            "relation": _NEXT_RANK_RELATION_HINT.get(edge.edge_type, ""),
        })

    return {
        "ok": True,
        "concept_id": concept_id,
        "neighbors": neighbors,
    }


@router.get("/concepts/{concept_id}")
def get_concept_by_id(concept_id: str):
    ge = _get_graph_editor()
    node = ge.get_concept(concept_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"ConceptNode {concept_id} not found")
    return _concept_to_dict(node)


@router.patch("/concepts/{concept_id}")
def update_concept(concept_id: str, req: ConceptNodeRequest):
    """Update a ConceptNode. Only fields present in the request are touched.

    Dedupes by ``idempotency_key`` (when supplied) so retries don't
    fire duplicate broadcasts + log entries.
    """
    cached = _idempotency_lookup(req.workspace_id, concept_id, req.idempotency_key)
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    updates: Dict[str, Any] = {}
    # Pydantic v1 / v2 compatible: only forward fields the client actually set.
    payload = req.dict(exclude_unset=True) if hasattr(req, "dict") else req.model_dump(exclude_unset=True)
    for key in (
        "name", "description", "data", "rendering", "backing_pointer",
        "provenance", "workspace_id", "layout_xy", "ui_state", "type_hint",
    ):
        if key in payload:
            updates[key] = payload[key]
    # Capture pre-update state for the evolution log (C5 / §8D.33).
    pre_node = ge.get_concept(concept_id)
    pre_dict = _concept_to_dict(pre_node) if pre_node else None

    node = ge.update_concept(concept_id, **updates)
    if node is None:
        raise HTTPException(status_code=404, detail=f"ConceptNode {concept_id} not found")
    node_dict = _concept_to_dict(node)
    # ``embed_fields_changed`` is auto-detected from the pre/post diff
    # — no need for the routes layer to peek at PATCH payload keys.
    refreshed = _apply_update_lifecycle(
        node, ge, pre_dict=pre_dict, node_dict=node_dict,
    )
    response = refreshed or node_dict
    _idempotency_store(req.workspace_id, concept_id, req.idempotency_key, response)
    return response


@router.delete("/concepts/{concept_id}")
def delete_concept_by_id(concept_id: str):
    # §8D.12 — foundation fixtures are undeletable. Return a clean 409
    # before doing any DB work or emitting lifecycle frames; the service
    # layer also guards (defense in depth), but surfacing it here keeps
    # the error message readable instead of silently no-op'ing.
    if concept_id.startswith("fixture::"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Concept {concept_id!r} is a §8D.12 foundation fixture "
                "and cannot be deleted."
            ),
        )
    ge = _get_graph_editor()
    # Capture pre-delete state so the evolution log retains a rollback
    # payload (C5 / §8D.33).
    pre_node = ge.get_concept(concept_id)
    pre_dict = _concept_to_dict(pre_node) if pre_node else None
    ok = ge.delete_concept(concept_id)
    _apply_delete_lifecycle(concept_id, pre_dict, ge)
    return {"ok": bool(ok), "concept_id": concept_id}


# ---------------------------------------------------------------------------
# §9.11 — Workspace purge
# ---------------------------------------------------------------------------

class PurgeWorkspaceRequest(BaseModel):
    """Delete every concept node + edge in a workspace.

    Optional ``confirm`` token must equal ``"erase"`` so accidental
    invocation can't drop a workspace silently. Returns counts of
    everything removed plus the emitted ``purge_workspace`` WS frame
    sequence number.
    """
    workspace_id: str = ""
    confirm: str = ""


@router.post("/purge_workspace")
async def purge_workspace(req: PurgeWorkspaceRequest):
    """§9.11 — wipe a workspace's concept graph + downstream caches.

    Walks every concept node in the workspace and calls
    ``apply_delete_lifecycle`` per card. That handles:

      * Kuzu node + edge deletion (via ``graph_editor.delete_concept``
        which the lifecycle calls).
      * ``concept_changed`` broadcasts so other tabs reflect each
        deletion (the consolidated purge frame fires too, but per-card
        events keep multi-tab views consistent during the walk).
      * Evolution log entries with actor ``user:_anon`` (rollback
        still works on the individual deletes).
      * ConceptIndex slot removal.
      * Output-projection schedule (3D scene drops the chunks).
      * Cascade scheduler cleanup for any agent parameter cards being
        purged.

    Then drops the workspace's LayoutFrame (3D coords) and emits a
    single ``purge_workspace`` WS frame so the frontend clears its
    apparition hint cache, concept-index cache, agent-token buffers,
    and frame_seq high-water marks in one pass.
    """
    if (req.confirm or "").lower() != "erase":
        raise HTTPException(
            status_code=400,
            detail="confirm token must equal 'erase' to acknowledge data loss",
        )
    ge = _get_graph_editor()
    ws = req.workspace_id or ""

    # Snapshot every concept node in the workspace before deletion so
    # we can drive the lifecycle one at a time. Loading the IDs first
    # keeps the iteration stable even if a peer creates a new card
    # during the walk (the new card stays — only what we listed is
    # purged). The per-card delete + lifecycle dispatch chain is
    # synchronous and can take seconds per card on a cold workspace
    # (first call triggers nomic embedder load through the concept-
    # index lifecycle hook). Offload the loop to a thread so the
    # asyncio event loop stays responsive for other requests.
    # §6.5 / §16.5 — the scan substrate the purge must ALSO empty: the
    # chunk pool (`/api/chunk_nodes` reads ChunkInstance), the trie +
    # snapshot lineage (stale content_hash rows would make the §16.5
    # re-scan rebuild silently incremental instead of clean), signal
    # fields, media/segment caches, and the legacy DomNode rows. Without
    # this the chunk pool never returned to baseline after a purge — the
    # §16.5 probe's step-5 cleanup contract caught it.
    _SCAN_SUBSTRATE_TABLES = (
        "ChunkInstance", "PageEmbedding", "ContentChunk",
        "TriePattern", "TrieVersion", "PatternLabel", "PatternEmbedding",
        "DomSnapshot", "Page", "Domain", "ContentTree",
        "SearchInputField", "PaginationField",
        "SegmentEmbedding", "SnapshotPatriciaIndex", "MediaAsset",
        "NodeLabel", "StructureTag", "DomNode",
    )

    def _purge_loop_blocking() -> int:
        # Bulk purge — raw Kuzu deletes only, no per-card service
        # cascade. The consolidated purge_workspace WS frame below
        # tells the frontend to clear its caches in one pass, which
        # subsumes per-card concept_changed broadcasts; the layout
        # drop below subsumes per-card output-projection schedules;
        # the concept-index hydrate-on-next-touch handles index
        # cleanup lazily (slots for deleted ids get pruned next time
        # they're read). Triggering the full lifecycle per card here
        # forced the nomic embedder to load synchronously inside the
        # delete loop and pushed a 2-card purge past 180s.
        purged = 0
        try:
            nodes = ge.list_concepts(workspace_id=ws, limit=100000) or []
            for n in nodes:
                try:
                    ge.delete_concept(n.concept_id)
                    purged += 1
                except Exception as e:
                    logger.warning("purge_workspace delete %s failed: %s",
                                   n.concept_id, e)
        except Exception as e:
            logger.warning("purge_workspace list_concepts failed: %s", e)
        # Scan-substrate wipe (best-effort per table; a missing table on a
        # minimal schema is fine). The workspace IS the chunk pool on this
        # single-user on-device app (§9.11), so a full-workspace purge
        # empties the pool — that's what makes the §16.5 purge → re-scan
        # → identical-rebuild contract checkable.
        try:
            conn = get_connection()
            for t in _SCAN_SUBSTRATE_TABLES:
                try:
                    conn.execute(f"MATCH (n:{t}) DETACH DELETE n")
                except Exception:
                    pass
        except Exception as e:
            logger.warning("purge_workspace scan-substrate wipe failed: %s", e)
        return purged

    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()
    nodes_purged = await loop.run_in_executor(None, _purge_loop_blocking)

    # Drop the LayoutFrame for this workspace so chunks don't linger
    # in 3D after the purge.
    layout_dropped = False
    try:
        from backend.services.layout_service import get_layout_service
        layout = get_layout_service(broadcast=_ws_push)
        layout_dropped = layout.purge_workspace(workspace_id=ws)
    except Exception as e:
        logger.warning("purge_workspace layout drop failed: %s", e)

    # persistence.md §1.8 / §18.4 / §16.5 — drop the TF-IDF rows. The store
    # is one ever-growing accumulator; the bulk Kuzu delete above removes
    # the ChunkInstance nodes but NOT these in-memory vectors, so without
    # this a post-purge ``chunk_search`` would surface ghost rows (score +
    # preview, empty html_raw). A FULL-workspace purge clears EVERYTHING
    # (``clear_all`` — scanner-emitted instance rows are URL-keyed, not
    # ``graph__``-prefixed, so the workspace-prefix removal alone left them
    # behind; the §16.5 probe's baseline check caught it). Cheap CSR
    # rebuild — no embedder load — safe in this perf-sensitive bulk path.
    tfidf_rows_dropped = 0
    try:
        from backend.services.global_tfidf_store import get_default_store
        store = get_default_store()
        tfidf_rows_dropped = store.remove_workspace(ws) + store.clear_all()
    except Exception as e:
        logger.warning("purge_workspace tfidf drop failed: %s", e)

    # Drop the UI state mirror so selected/pinned ids don't dangle
    # past their concept-id's existence.
    try:
        from backend.services.ui_state_service import get_ui_state_service
        get_ui_state_service(broadcast=_ws_push).clear_workspace(ws)
    except Exception as e:
        logger.warning("purge_workspace UI state drop failed: %s", e)
    # Drop the telemetry ring buffer too — purges typically run between
    # test scenarios; leftover entries would skew the new run's drain.
    try:
        from backend.services.ui_telemetry_service import get_ui_telemetry_service
        get_ui_telemetry_service(broadcast=_ws_push).clear_workspace(ws)
    except Exception as e:
        logger.warning("purge_workspace telemetry drop failed: %s", e)

    # §8D.39.6 — drop the backing-pointer version registry for this
    # workspace so re-materialised compiled-from-scans nodes start
    # fresh at version 1.
    try:
        from backend.services import backing_version
        backing_version.reset(ws)
    except Exception as e:
        logger.warning("purge_workspace backing_version reset failed: %s", e)

    # Reset the WS frame_seq counter so a fresh subscription starts
    # at seq=1 (otherwise the frontend's out-of-order guard would
    # think the next bootstrap is stale).
    try:
        from backend.api.ws_frames import reset_frame_seq
        reset_frame_seq(ws or "_default")
    except Exception:
        pass

    # Emit the consolidated purge frame so the frontend clears its
    # apparition / concept-index / agent-token caches in one go.
    try:
        from backend.api.ws_frames import build_purge_workspace
        _ws_push(0, build_purge_workspace(workspace_id=ws or "_default"))
    except Exception as e:
        logger.warning("purge_workspace frame emit failed: %s", e)

    return {
        "ok": True,
        "workspace_id": ws,
        "nodes_purged": nodes_purged,
        "layout_dropped": layout_dropped,
        "tfidf_rows_dropped": tfidf_rows_dropped,
    }


class CleanupTestArtifactsRequest(BaseModel):
    """§R.9 — janitor sweep over one-off test-DB garbage."""
    max_age_hours: float = 24.0


@router.post("/maintenance/cleanup_test_artifacts")
def cleanup_test_artifacts(req: CleanupTestArtifactsRequest):
    """§R.9 — run the db_janitor retention sweeps through the integrated
    stack so the REPL can hard-verify hygiene (§R.8):

      * stale one-off temp DB dirs (canonical ``wfh_test_`` prefix + the
        legacy prefix zoo) older than ``max_age_hours``;
      * per-workspace side files (``concept_index_*`` / ``evolution_log_*`` /
        ``layout_frame_*``) for **test-convention** (``ws_``-prefixed)
        workspaces only — ``_default`` and human-named workspaces are never
        touched.
    """
    from backend.services.db_janitor import sweep_all
    report = sweep_all(max_age_hours=req.max_age_hours)
    return {"ok": True, **report}


# ---------------------------------------------------------------------------
# C5 / §8D.33 — Evolution log REST endpoints
# ---------------------------------------------------------------------------

@router.get("/evolution_log")
def list_evolution_log(
    workspace_id: str = "",
    actor: Optional[str] = None,
    target_prefix: Optional[str] = None,
    limit: int = 200,
):
    from backend.services.evolution_log import get_evolution_log
    ge = _get_graph_editor()
    log = get_evolution_log(graph_editor=ge)
    diffs = log.list_diffs(
        workspace_id=workspace_id,
        actor=actor,
        target_prefix=target_prefix,
        limit=int(limit),
    )
    return {"diffs": [d.to_dict() for d in diffs]}


class RollbackSingleRequest(BaseModel):
    edit_id: int
    workspace_id: str = ""


@router.post("/evolution_log/rollback")
def rollback_evolution(req: RollbackSingleRequest):
    from backend.services.evolution_log import get_evolution_log
    ge = _get_graph_editor()
    return get_evolution_log(graph_editor=ge).rollback_single(
        edit_id=int(req.edit_id), workspace_id=req.workspace_id,
    )


class RollbackRangeRequest(BaseModel):
    edit_id_low: int
    edit_id_high: int
    workspace_id: str = ""


@router.post("/evolution_log/rollback_range")
def rollback_evolution_range(req: RollbackRangeRequest):
    from backend.services.evolution_log import get_evolution_log
    ge = _get_graph_editor()
    return get_evolution_log(graph_editor=ge).rollback_range(
        edit_id_low=int(req.edit_id_low),
        edit_id_high=int(req.edit_id_high),
        workspace_id=req.workspace_id,
    )


class RollbackActorRequest(BaseModel):
    actor: str
    since_timestamp: float
    workspace_id: str = ""


@router.post("/evolution_log/rollback_actor")
def rollback_evolution_actor(req: RollbackActorRequest):
    from backend.services.evolution_log import get_evolution_log
    ge = _get_graph_editor()
    return get_evolution_log(graph_editor=ge).rollback_actor_since(
        actor=req.actor,
        since_timestamp=float(req.since_timestamp),
        workspace_id=req.workspace_id,
    )


@router.post("/recompute_concept_index")
def recompute_concept_index(workspace_id: str = ""):
    """Trigger the batch SIMILAR_TO + PageRank pass (§11.6).

    Returns counts of slots that changed. The service emits
    ``concept_index_update`` frames on the WS for every changed slot
    so live frontends pick up the new ranks/neighbours immediately.
    """
    try:
        from backend.services.concept_index_service import get_concept_index_service
        ge = _get_graph_editor()
        svc = get_concept_index_service(broadcast=_ws_push, graph_editor=ge)
        result = svc.recompute_all(workspace_id=workspace_id)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _get_apparition_service():
    """Return the process-wide ApparitionService bound to live indices.

    Uses the §1.1 singleton-via-accessor pattern so the §1.9 multi-
    frequency mode counter survives across REST calls. The index +
    graph_editor are rebound on every call so a late-init concept
    index is wired without losing the utility-event tally.
    """
    from backend.services.concept_index_service import get_concept_index_service
    from backend.services.apparition_service import get_apparition_service
    ge = _get_graph_editor()
    ci = get_concept_index_service(broadcast=_ws_push, graph_editor=ge)
    return get_apparition_service(concept_index=ci, graph_editor=ge)


@router.get("/apparitions/mode")
def get_apparitions_mode():
    """Report the ApparitionService active ranking mode per §1.9.

    Returns ``{"mode": "single_frequency" | "multi_frequency",
    "events": int, "threshold": int, "bands": [...], "band_weights": {...}}``.

    Used by the pinned-panel chrome to render the mode badge and by
    the ``apparition-mode-roundtrip`` env-scenario to verify the
    transition fires at the correct event threshold (anti-goal §18.25).
    """
    svc = _get_apparition_service()
    return svc.get_mode()


@router.post("/apparitions/record_utility")
def record_apparition_utility(payload: Dict[str, Any]):
    """Record one observed-utility event per §1.9.

    Body ``{"band": "token"|"phrase"|"paragraph"|"document"|"pattern",
    "weight": float?}``. Called by the lifecycle dispatcher whenever a
    surfaced halo candidate transitions soft→hard or otherwise marks
    itself as useful (pin, compile, autoregressive walk).
    """
    band = str(payload.get("band") or "token")
    weight = float(payload.get("weight") or 1.0)
    svc = _get_apparition_service()
    svc.record_utility_event(band=band, weight=weight)
    return {"ok": True, **svc.get_mode()}


@router.get("/apparitions/{focal_id}")
def get_apparitions(
    focal_id: str,
    workspace_id: str = "",
    k: int = 10,
    min_score: float = 0.0,
    transport: bool = False,
    ray_project: bool = False,
):
    """Top-K candidates for a focal concept node via triple-product (§8D.43).

    Used by the editor's hover-apparition surface (§8D.16) — frontend
    calls this on hover of any stuck concept card. With ``transport=1`` each
    candidate also carries §O.18 cone-ray transport scalars for the 3D
    projector (radial + along_ray from normalized similarity; angular is
    camera-computed client-side along the cone surface normal). With
    ``ray_project=1`` (§8.2.1.1) the halo is augmented with the
    manifold-nearest projector chunks from the LayoutService 6D-UMAP frame
    (each already carrying manifold-derived cone transport).
    """
    svc = _get_apparition_service()
    results = svc.apparitions_for_focal(
        focal_id, workspace_id=workspace_id, k=int(k), min_score=float(min_score),
        ray_project=bool(ray_project),
    )
    if transport and results:
        # §O.18 — closer-on-cone == more similar. Normalize each score to the
        # top candidate, then radial = (1-s)·R (most-similar nearest the apex)
        # and along_ray = s·R. R matches the layout target sphere (§O.17 / B.3).
        # Ray-projected candidates already carry manifold-derived transport
        # (§8.2.1.1) — leave theirs intact.
        _CONE_R = 40.0
        smax = max((r.score for r in results), default=0.0) or 1.0
        for r in results:
            if getattr(r, "ray_projected", False) and r.transport:
                continue
            s = (r.score / smax) if smax else 0.0
            r.transport = {
                "similarity": round(s, 6),
                "radial": round((1.0 - s) * _CONE_R, 4),
                "along_ray": round(s * _CONE_R, 4),
            }
    return {"focal_id": focal_id, "candidates": [r.to_dict() for r in results]}


@router.post("/radiation")
def get_radiation(payload: Dict[str, Any] = Body(...)):
    """Empty-primitive radiation for a typed-text query (§8D.22).

    Body: ``{ text: str, workspace_id?: str, k?: int }``.
    Returns top-K candidates ranked by triple-product against the
    synthetic description embedding of ``text``.
    """
    text = str(payload.get("text") or "")
    workspace_id = str(payload.get("workspace_id") or "")
    k = int(payload.get("k") or 10)
    svc = _get_apparition_service()
    results = svc.radiation_for_text(text, workspace_id=workspace_id, k=k)
    return {"query": text, "candidates": [r.to_dict() for r in results]}


@router.get("/ontology_walk/{focal_id}")
def get_ontology_walk(
    focal_id: str,
    workspace_id: str = "",
    k: int = 20,
    depth: int = 1,
):
    """DB-ontology recursion neighbours (§8D.36.3).

    Walks typed edges from the focal up to ``depth`` and returns the
    connected concept-graph subset, sorted by distance ascending.
    Used by the editor when hovering Database / Module / committed
    subgraph cards.
    """
    svc = _get_apparition_service()
    return {
        "focal_id": focal_id,
        "neighbours": svc.ontology_neighbours(
            focal_id, workspace_id=workspace_id, k=int(k), depth=int(depth),
        ),
    }


@router.get("/concept_completions")
def get_concept_completions(prefix: str = "", workspace_id: str = "", k: int = 12):
    """§8D.1.3 — auto-complete over concept names for the
    ``{partial_name}`` reference flow. Used by the editor when the
    user types into a new field's name cell.

    Returns concepts whose name starts with ``prefix`` (case-
    insensitive), then concepts whose name *contains* it (also CI),
    sorted by name length ascending so shorter matches surface first.
    The response shape is intentionally minimal — name + concept_id +
    type_hint — so the frontend can drop the completion directly into
    the cursor without a follow-up fetch.
    """
    if not prefix:
        return {"prefix": prefix, "completions": []}
    ge = _get_graph_editor()
    needle = prefix.lower().strip()
    all_concepts = ge.list_concepts(workspace_id=workspace_id, limit=2000) or []
    starts: List[Dict[str, Any]] = []
    contains: List[Dict[str, Any]] = []
    for c in all_concepts:
        name = (getattr(c, "name", "") or "")
        if not name:
            continue
        lower = name.lower()
        if lower.startswith(needle):
            starts.append({
                "concept_id": c.concept_id,
                "name":       name,
                "type_hint":  getattr(c, "type_hint", "") or "",
            })
        elif needle in lower:
            contains.append({
                "concept_id": c.concept_id,
                "name":       name,
                "type_hint":  getattr(c, "type_hint", "") or "",
            })
    starts.sort(key=lambda d: (len(d["name"]), d["name"]))
    contains.sort(key=lambda d: (len(d["name"]), d["name"]))
    out = (starts + contains)[: max(0, int(k))]
    return {"prefix": prefix, "completions": out}


@router.get("/closest_inverse/{output_id}")
def get_closest_inverse(output_id: str, workspace_id: str = "", k: int = 10):
    """Closest-inverse function lookup (§8D.7 / §R.6).

    Given an output concept node, return input-candidates whose
    forward-execution would produce something close to it. Recorded
    ``FORWARD_MAPPED_TO`` mappings rank first (``provenance =
    "recorded-mapping"``); nomic-similarity generalisation fills the rest.
    """
    svc = _get_apparition_service()
    results = svc.closest_inverse(output_id, workspace_id=workspace_id, k=int(k))
    return {"output_id": output_id, "candidates": [r.to_dict() for r in results]}


@router.get("/inverse_map/{node_id}")
def get_inverse_map(node_id: str, workspace_id: str = ""):
    """§R.6 — the node's FULL recorded forward-mapping state space.

    ``as_output`` — every recorded forward call INTO this node (the exact
    inverse: which inputs, under which function signature); ``as_input`` —
    every recorded mapping FROM this node. Pure read over the one
    ``ConceptEdge`` table (edge_type ``FORWARD_MAPPED_TO``).
    """
    from backend.services.forward_inverse_map import inverse_map
    ge = _get_graph_editor()
    out = inverse_map(ge, node_id, workspace_id=workspace_id)
    return {
        "ok": True,
        **out,
        "count": len(out.get("as_output", [])) + len(out.get("as_input", [])),
    }


# ---------------------------------------------------------------------------
# W9 / §8D.39 — Compiled-In-From-Scans concept-card materialisation
# ---------------------------------------------------------------------------

def _get_compiled_materialiser():
    from backend.services.compiled_from_scans import CompiledFromScansMaterialiser
    from backend.services.concept_index_service import get_concept_index_service
    ge = _get_graph_editor()
    ci = get_concept_index_service(broadcast=_ws_push, graph_editor=ge)
    return CompiledFromScansMaterialiser(graph_editor=ge, concept_index=ci)


class SearchableUrlRequest(BaseModel):
    url: str
    search_field_xpath: str
    query_param_name: str = "q"
    pagination_button_xpath: str = ""
    detected_at: str = ""
    workspace_id: str = ""


class DetectedAccessorRequest(BaseModel):
    url: str
    xpath: str
    field_type: str
    text_hint: str = ""
    workspace_id: str = ""


class XPathPatternRequest(BaseModel):
    domain: str
    pattern: str
    accessor_map: Optional[Dict[str, str]] = None
    instance_count: int = 0
    workspace_id: str = ""


@router.post("/compiled/searchable_url")
def materialise_searchable_url(req: SearchableUrlRequest):
    """§8D.39.1 — auto-instantiate a SearchableURL concept node."""
    mat = _get_compiled_materialiser()
    return mat.materialise_searchable_url(
        url=req.url,
        search_field_xpath=req.search_field_xpath,
        query_param_name=req.query_param_name,
        pagination_button_xpath=req.pagination_button_xpath,
        detected_at=req.detected_at,
        workspace_id=req.workspace_id,
    ) or {"status": "skipped"}


@router.post("/compiled/detected_accessor")
async def materialise_detected_accessor(req: DetectedAccessorRequest):
    """§8D.39.2 — auto-instantiate a DetectedAccessor concept node.

    Async + fully executor-offloaded — both the materialiser singleton
    init (which lazy-loads the ConceptIndexService / nomic embedder)
    and the create_concept + upsert_slot pipeline run off the event
    loop so concurrent REST + WS traffic stays responsive.
    """
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()

    def _blocking() -> Dict[str, Any]:
        mat = _get_compiled_materialiser()
        return mat.materialise_detected_accessor(
            url=req.url,
            xpath=req.xpath,
            field_type=req.field_type,
            text_hint=req.text_hint,
            workspace_id=req.workspace_id,
        ) or {"status": "skipped"}

    return await loop.run_in_executor(None, _blocking)


@router.post("/compiled/xpath_pattern")
async def materialise_xpath_pattern(req: XPathPatternRequest):
    """§8D.39.3 / §5.4 — auto-instantiate an XPathPattern concept node.

    Async + fully executor-offloaded — see ``materialise_detected_accessor``
    for the lifecycle / embedder rationale.
    """
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()

    def _blocking() -> Dict[str, Any]:
        mat = _get_compiled_materialiser()
        return mat.materialise_xpath_pattern(
            domain=req.domain,
            pattern=req.pattern,
            accessor_map=req.accessor_map,
            instance_count=req.instance_count,
            workspace_id=req.workspace_id,
        ) or {"status": "skipped"}

    return await loop.run_in_executor(None, _blocking)


# ---------------------------------------------------------------------------
# §8D.4.2 — Python-native Object/Property/Function tree materialisation
# ---------------------------------------------------------------------------

def _get_python_api_materialiser():
    from backend.services.python_api_materialiser import PythonAPIMaterialiser
    from backend.services.concept_index_service import get_concept_index_service
    ge = _get_graph_editor()
    ci = get_concept_index_service(broadcast=_ws_push, graph_editor=ge)
    return PythonAPIMaterialiser(graph_editor=ge, concept_index=ci)


class PythonApiMaterialiseRequest(BaseModel):
    qualified_name: str  # e.g. "backend.services.selenium_client.WebBrowserManager"
    workspace_id: str = ""
    max_depth: int = 1


class PythonApiMaterialiseModuleRequest(BaseModel):
    module_path: str  # e.g. "wfh_imports" — a module of import statements
    workspace_id: str = ""
    max_walk_depth: int = 4


@router.post("/python_api/materialise")
async def materialise_python_api(req: PythonApiMaterialiseRequest):
    """§8D.4.2 — project a Python class into Object/Property/Function
    ConceptNode trees with the read-only + no_datablock sentinels.

    Idempotent on qualified name. Re-running against the same target
    refreshes existing records in place (with backing-pointer version
    bumps per §8D.39.6 so dependent compiles re-fire).
    """
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()

    def _blocking() -> Dict[str, Any]:
        mat = _get_python_api_materialiser()
        result = mat.materialise_qualified_name(
            req.qualified_name,
            workspace_id=req.workspace_id,
            max_depth=int(req.max_depth or 1),
        )
        if result is None:
            return {
                "status": "skipped",
                "reason": "import or class resolution failed",
                "qualified_name": req.qualified_name,
            }
        return {
            "status": "ok",
            "object": result,
            "qualified_name": req.qualified_name,
        }

    return await loop.run_in_executor(None, _blocking)


@router.post("/python_api/materialise_module")
async def materialise_python_api_module(req: PythonApiMaterialiseModuleRequest):
    """§9.7 / §1.2 — library-imports middleware. Import a module of `import`
    statements (the workspace's `wfh_imports.py` convention) and materialise an
    Object/Property/Function ConceptNode tree for every top-level imported
    class. Generalises `/python_api/materialise` from one class to a whole
    imports module. Idempotent on qualified name.
    """
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()

    def _blocking() -> Dict[str, Any]:
        mat = _get_python_api_materialiser()
        roots = mat.materialise_module(
            req.module_path,
            workspace_id=req.workspace_id,
            max_walk_depth=int(req.max_walk_depth or 4),
        )
        return {
            "status": "ok" if roots else "skipped",
            "module_path": req.module_path,
            "root_count": len(roots),
            "roots": roots,
        }

    return await loop.run_in_executor(None, _blocking)


@router.post("/python_api/rematerialise_module")
async def rematerialise_python_api_module(req: PythonApiMaterialiseModuleRequest):
    """§2.4 / §3.3 — the explicit `materialiser-reimport` action. Re-walk an
    imports module after it changed: add new classes, refresh existing in
    place (backing-version bump), and GC the subtrees of classes no longer
    imported (scoped to this module — never the fixtures). The §3.3 alternative
    to an OS file-watcher.
    """
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()

    def _blocking() -> Dict[str, Any]:
        mat = _get_python_api_materialiser()
        diff = mat.re_materialise(
            req.module_path,
            workspace_id=req.workspace_id,
            max_walk_depth=int(req.max_walk_depth or 4),
        )
        return {"status": "ok", "module_path": req.module_path, **diff}

    return await loop.run_in_executor(None, _blocking)


# ---------------------------------------------------------------------------
# W31 / §8C.7 / §8D.5 / §8D.27 — ConceptComputeNode compile endpoints
#
# The ConceptComputeNode primitive turns any concept node into a callable
# LangGraph node that resolves {ref} placeholders, runs through the
# kind-dispatch (plain / prompt / structured / python), optionally calls
# the on-device SLM with a Pydantic-validated schema, and writes the
# result back into the node's rendering field via the standard lifecycle.
#
# Two endpoints:
#   POST /api/conceptual/compile       — compile a single concept node
#   POST /api/conceptual/compile_chain — walk back-references and chain-compile
#
# Both async-offloaded so SLM calls (or the deterministic stub) don't
# block the event loop.
# ---------------------------------------------------------------------------

class ConceptComputeRequest(BaseModel):
    concept_id: str
    use_slm: bool = True
    persist_rendering: bool = True
    # §8D.7 — compile = forward call + inverse closest lookup, fused.
    # The frontend no longer needs a separate INVERSE button: every
    # compile press also surfaces top-K inverse candidates so the user
    # can browse "what inputs would have produced something close to
    # this?" without an extra click. Set to 0 to suppress.
    inverse_k: int = 6


class ConceptComputeChainRequest(BaseModel):
    focal_id: str
    workspace_id: str = ""
    max_depth: int = 4
    use_slm: bool = True


def _make_slm_for_compute(use_slm: bool):
    """Return an SLMClient when ``use_slm=True``, else ``None``.

    The SLMClient constructor is lazy (it does NOT load the GGUF here),
    so construction does not fail on a missing model. A real load failure
    surfaces later as ``SLMUnavailableError`` (mapped to HTTP 503) on
    first use — §8D.46 forbids a silent real→stub fallback in production.
    ``None`` here means only "the caller did not request the SLM"
    (``use_slm=False``), a legitimate no-SLM compute."""
    if not use_slm:
        return None
    from backend.services.slm_client import SLMClient
    return SLMClient()


@router.post("/conceptual/compile")
async def conceptual_compile(req: ConceptComputeRequest):
    """Compile a single concept node into its rendering AND its
    closest-inverse candidate set (§8D.7 fused contract).

    Returns the diagnostic dict from ``ConceptComputeNode.compile()``,
    augmented with:

      * ``inverse_candidates`` — top-K outputs whose forward execution
        would produce something close to this card. Driven by
        ``apparition_service.closest_inverse(concept_id, k=req.inverse_k)``.
      * ``io_signature``       — parsed from the data block when
        available (§8D.4) — input/output type hints so the frontend
        wiring suggester has something concrete to offer.
    """
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()

    def _blocking() -> Dict[str, Any]:
        from backend.services.conceptual_compute import (
            ConceptComputeNode, ComputeNodeSpec,
        )
        ge = _get_graph_editor()
        slm = _make_slm_for_compute(req.use_slm)
        node = ConceptComputeNode(
            req.concept_id,
            graph_editor=ge,
            slm_client=slm,
            broadcast=_ws_push,
            persist_rendering=req.persist_rendering,
        )
        out = node.compile()
        # Fuse the closest-inverse lookup. Compile = forward + inverse.
        if req.inverse_k > 0:
            try:
                svc = _get_apparition_service()
                concept = ge.get_concept(req.concept_id)
                ws = (concept.workspace_id or "") if concept else ""
                results = svc.closest_inverse(
                    req.concept_id, workspace_id=ws, k=int(req.inverse_k),
                )
                out["inverse_candidates"] = [r.to_dict() for r in results]
            except Exception as exc:
                logger.debug("inverse fold-in failed: %s", exc)
                out["inverse_candidates"] = []
        else:
            out["inverse_candidates"] = []
        # Surface the parsed I/O signature so the frontend can render
        # input/output port hints WITHOUT a second round-trip. §8D.4 / §131.
        try:
            concept = ge.get_concept(req.concept_id)
            if concept is not None:
                spec = ComputeNodeSpec.from_concept(concept)
                out["io_signature"] = {
                    "kind":           spec.kind,
                    "input_types":    list(spec.inputs.keys()) if spec.inputs else [],
                    "output_schema":  spec.output_schema,
                    "python_entry":   spec.python_entry,
                    "has_prompt":     bool(spec.prompt),
                }
        except Exception as exc:
            logger.debug("io_signature build failed: %s", exc)
            out["io_signature"] = {"kind": out.get("kind", "")}
        return out

    return await loop.run_in_executor(None, _blocking)


@router.post("/conceptual/compile_chain")
async def conceptual_compile_chain(req: ConceptComputeChainRequest):
    """Walk back-references from ``focal_id`` and compile the chain.

    Returns ``{ordered: [concept_id, ...], state: {cid: {rendering, kind, ...}}}``
    where the state dict carries each compiled node's diagnostic.
    """
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()

    def _blocking() -> Dict[str, Any]:
        from backend.services.conceptual_compute import (
            compile_subgraph_to_langgraph,
        )
        ge = _get_graph_editor()
        slm = _make_slm_for_compute(req.use_slm)
        app, ordered = compile_subgraph_to_langgraph(
            req.focal_id,
            graph_editor=ge,
            slm_client=slm,
            broadcast=_ws_push,
            workspace_id=req.workspace_id,
            max_depth=req.max_depth,
        )
        try:
            state = app.invoke({})
        except Exception as exc:
            logger.warning("Compile-chain invoke failed: %s", exc)
            return {"ordered": ordered, "error": str(exc), "state": {}}
        return {"ordered": ordered, "state": state}

    return await loop.run_in_executor(None, _blocking)


# ---------------------------------------------------------------------------
# D3 / §8D.13 — Per-sample iteration: pattern instance resolution
# ---------------------------------------------------------------------------

@router.get("/pattern_instances/{concept_id}")
def get_pattern_instances(concept_id: str, workspace_id: str = ""):
    """§8D.13 — Resolve an XPathPattern concept node to its instance bank.

    When the user binds a card to an XPathPattern (via a {ref}), the
    pattern's matching chunk instances become the iteration domain.
    The stepper UI navigates this list one sample at a time.

    Returns ``{ pattern, instances: [{instance_id, rendered_text, fields}] }``.
    """
    try:
        ge = _get_graph_editor()
        node = ge.get_concept(concept_id)
        if node is None or node.type_hint != "xpath_pattern":
            return {"pattern": None, "instances": []}
        try:
            meta = json.loads(node.data) if node.data else {}
        except Exception:
            meta = {}
        pattern = meta.get("pattern") or ""
        if not pattern:
            return {"pattern": None, "instances": []}
        # Query Kuzu for ChunkInstance rows matching this pattern.
        conn = get_connection()
        try:
            res = conn.execute(
                "MATCH (ci:ChunkInstance)-[:INSTANCE_OF]->(tp:TriePattern) "
                "WHERE tp.pattern = $pat "
                "RETURN ci.instance_id, ci.rendered_text, ci.fields_json, ci.absolute_xpath "
                "LIMIT 200",
                parameters={"pat": pattern},
            )
            rows = []
            while res.has_next():
                r = res.get_next()
                rows.append({
                    "instance_id": r[0],
                    "rendered_text": r[1] or "",
                    "fields_json": r[2] or "",
                    "absolute_xpath": r[3] or "",
                })
            return {"pattern": pattern, "instances": rows}
        except Exception as e:
            return {"pattern": pattern, "instances": [], "error": str(e)}
    except Exception as e:
        return {"pattern": None, "instances": [], "error": str(e)}


# ---------------------------------------------------------------------------
# D1 / §8D.2.1 — Compile pipeline (cypher detection in data blocks)
# ---------------------------------------------------------------------------

class CompileRequest(BaseModel):
    text: str
    workspace_id: str = ""


@router.post("/compile_pipeline")
def compile_pipeline(req: CompileRequest):
    """§8D.2.1 / §R.5 — Compile a data block: cypher detection + the full
    syntax-agnostic rendering tree + the canonical top-level decomposition.

    Body: ``{ text: str, workspace_id?: str }``
    Returns: ``{ rewritten, trace, rendering, entries }`` where

      * ``rewritten``/``trace`` — cypher segments auto-detected (```cypher
        fences or whole-block statements), executed against Kuzu, results
        substituted in place;
      * ``rendering`` — the §8D.20 syntax-free clean-text tree over the
        resolved text (JSON, §R.5 markdown-gesture outline, indent tree, or
        verbatim plain text);
      * ``entries`` — ``[{key, value}]``, the canonical top-level
        decomposition a compile-expand turns into child cards — the same
        children on every surface (§R.1 commutation / §R.8 REPL anchor).
    """
    from backend.services.compile_pipeline import (
        resolve_cypher_in_data, compute_rendering_tree, decompose_top_level,
    )
    try:
        conn = get_connection()
    except Exception:
        conn = None
    text = req.text or ""
    out = resolve_cypher_in_data(text, db_conn=conn)
    ge = None
    try:
        ge = _get_graph_editor()
    except Exception:
        ge = None
    try:
        out["rendering"] = compute_rendering_tree(text, ge=ge)
    except Exception as e:
        out["rendering_error"] = str(e)
    try:
        out["entries"] = decompose_top_level(out.get("rewritten") or text)
    except Exception as e:
        out["entries_error"] = str(e)
    return out


# ---------------------------------------------------------------------------
# W36 — Concept graph export / import
#
# NOTE — these routes are physically defined ABOVE ``/concepts/{concept_id}``
# (search for the block headed "W36 (early)" earlier in this file) so the
# static ``/export`` and ``/import`` path segments win FastAPI's first-match
# ordering. Keeping them down here would let ``{concept_id}`` capture them
# and 404 with "ConceptNode export not found".
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# W37 — Telemetry / observability dashboard
# ---------------------------------------------------------------------------

@router.get("/telemetry")
def telemetry(workspace_id: str = ""):
    """Aggregate workspace metrics for the observability dashboard."""
    out: Dict[str, Any] = {"workspace_id": workspace_id}
    try:
        ge = _get_graph_editor()
        concepts = ge.list_concepts(workspace_id=workspace_id, limit=10000)
        out["concept_count"] = len(concepts)
        # Breakdown by type_hint.
        by_type: Dict[str, int] = {}
        by_prov: Dict[str, int] = {}
        for n in concepts:
            t = n.type_hint or "untyped"
            by_type[t] = by_type.get(t, 0) + 1
            p = n.provenance or "unknown"
            by_prov[p] = by_prov.get(p, 0) + 1
        out["concepts_by_type"] = by_type
        out["concepts_by_provenance"] = by_prov
        out["edge_count"] = len(ge.list_concept_edges(workspace_id=workspace_id, limit=50000))
    except Exception as e:
        out["concept_error"] = str(e)
    try:
        from backend.services.evolution_log import get_evolution_log
        log = get_evolution_log()
        out["evolution_log_size"] = len(log.list_diffs(workspace_id=workspace_id, limit=100000))
    except Exception as e:
        out["evolution_log_error"] = str(e)
    try:
        from backend.services.review_queue import get_review_queue
        out["pending_reviews"] = len(get_review_queue().list_pending(workspace_id=workspace_id))
    except Exception as e:
        out["review_error"] = str(e)
    try:
        from backend.services.concept_index_service import get_concept_index_service
        ci = get_concept_index_service(broadcast=_ws_push, graph_editor=_get_graph_editor())
        slots = ci.list_slots(workspace_id=workspace_id)
        out["concept_index_size"] = len(slots)
        # Top-5 PageRank concepts.
        ranked = sorted(
            slots.items(), key=lambda kv: -float(getattr(kv[1], "pagerank", 0.0) or 0.0),
        )[:5]
        out["top_pagerank"] = [
            {"card_id": cid, "pagerank": float(getattr(s, "pagerank", 0.0) or 0.0)}
            for cid, s in ranked
        ]
    except Exception as e:
        out["concept_index_error"] = str(e)
    try:
        with _stream_lock:
            out["active_snapshot_ws"] = len(_stream_queues)
            snapshot_sizes = {str(sid): q.qsize() for sid, q in _stream_queues.items()}
        with _workspace_lock:
            out["active_workspace_ws"] = len(_workspace_queues)
            workspace_sizes = {wid: q.qsize() for wid, q in _workspace_queues.items()}
        out["ws_queue_sizes"] = {
            "snapshot": snapshot_sizes,
            "workspace": workspace_sizes,
        }
        out["ws_drops"] = get_ws_drop_counts()
    except Exception:
        pass
    return out


@router.get("/health")
def health():
    """Lightweight liveness + backpressure snapshot.

    Returns a small dict instead of the heavier ``/api/telemetry``
    payload, so operators can poll it cheaply (every few seconds)
    without DB hits. Surfaces:

      * ``ok``               — always True if the process is up.
      * ``ws_drops``         — per-queue dropped-frame counters since
        process start. Non-zero means slow consumers.
      * ``ws_queue_sizes``   — current depth per active queue.
      * ``settings``         — the live tunables an operator wants to
        check before tuning (queue max, idempotency TTL, cascade caps).
    """
    out: Dict[str, Any] = {"ok": True}
    try:
        out["ws_drops"] = get_ws_drop_counts()
        with _stream_lock:
            out.setdefault("ws_queue_sizes", {})["snapshot"] = {
                str(sid): q.qsize() for sid, q in _stream_queues.items()
            }
        with _workspace_lock:
            out.setdefault("ws_queue_sizes", {})["workspace"] = {
                wid: q.qsize() for wid, q in _workspace_queues.items()
            }
        from backend.services.settings import get_settings
        s = get_settings()
        out["settings"] = {
            "ws_queue_max": s.ws_queue_max,
            "idempotency_ttl_sec": s.idempotency_ttl_sec,
            "cascade_debounce_sec": s.cascade_debounce_sec,
            "cascade_max_ticks_per_min": s.cascade_max_ticks_per_min,
            "spawn_max_per_workspace_per_min": s.spawn_max_per_workspace_per_min,
            "agent_token_buffer_size": s.agent_token_buffer_size,
        }
    except Exception as e:
        out["error"] = str(e)
    return out


@router.get("/subsystem_status")
def subsystem_status():
    """§8D.46 — report whether each runtime subsystem (SLM, embedder,
    selenium scanner, langgraph) is using the real implementation
    or a stub/fallback.

    Returns a dict per subsystem with ``backend``, ``loaded``, plus
    subsystem-specific fields. Operators + the REPL ``subsystem-status``
    action use this to enforce the no-mocks invariant: ANY ``backend ==
    "stub"`` / ``backend == "fake"`` in production is a contract
    violation.

    Reads are cheap — they touch existing singletons + a couple of
    importlib lookups; no model load is triggered by introspection.
    """
    out: Dict[str, Any] = {"ok": True}

    # SLM (§8D.8) — GPT4All Nous Hermes Mistral 2 DPO (or smaller fallback).
    try:
        from backend.services.slm_client import SLMClient
        out["slm"] = SLMClient().status()
    except Exception as e:
        out["slm"] = {"backend": "error", "error": str(e)}

    # Embedder (§8D.17) — nomic v1.5 by default.
    try:
        from backend.services.embedding_service import EmbeddingService
        # Don't trigger a load just to introspect; only report status
        # if a service was already constructed elsewhere.
        ee = getattr(_get_compiled_materialiser._cached_embedder, "_obj", None) \
            if hasattr(_get_compiled_materialiser, "_cached_embedder") else None
        if ee is None:
            # Construct one cheaply (lazy — model loads on first call,
            # not at construction unless the cache miss path runs).
            try:
                ee = EmbeddingService()
            except Exception as e:
                out["embedder"] = {"backend": "error", "error": str(e)}
                ee = None
        if ee is not None:
            out["embedder"] = ee.status()
    except Exception as e:
        out["embedder"] = {"backend": "error", "error": str(e)}

    # Selenium scanner — webdriver alive?
    try:
        no_webdriver = os.environ.get("NO_WEBDRIVER", "").lower() in ("1", "true", "yes")
        if no_webdriver:
            # §L.1 acceptance bar — keep `singleton_bound` present in BOTH
            # modes (false in stub since the driver is skipped) so consumers
            # can always read selenium.singleton_bound. The real path below
            # reports it true once the WebBrowserManager singleton is bound.
            out["selenium"] = {"backend": "skipped",
                               "loaded": False,
                               "singleton_bound": False,
                               "env": "NO_WEBDRIVER=1"}
        else:
            from backend.services.selenium_client import WebBrowserManager
            # WebBrowserManager() is a singleton via __new__; reading the
            # already-bound instance without re-running __init__ keeps the
            # introspection cheap (no driver re-init on every status call).
            mgr = WebBrowserManager._instance
            driver = getattr(mgr, "driver", None) if mgr is not None else None
            alive = False
            try:
                if driver is not None:
                    _ = driver.current_url
                    alive = True
            except Exception:
                alive = False
            out["selenium"] = {
                "backend":      "selenium" if alive else "uninitialised",
                "loaded":       alive,
                "driver_class": type(driver).__name__ if driver else None,
                "singleton_bound": mgr is not None,
            }
    except Exception as e:
        out["selenium"] = {"backend": "error", "error": str(e)}

    # LangGraph — importable?
    try:
        import importlib
        lg = importlib.import_module("langgraph.graph")
        out["langgraph"] = {
            "backend":  "langgraph",
            "loaded":   True,
            "has_StateGraph": hasattr(lg, "StateGraph"),
        }
    except Exception as e:
        out["langgraph"] = {"backend": "missing", "loaded": False, "error": str(e)}

    # Aggregate: True iff every subsystem reports a real backend.
    real_backends = {"gpt4all", "nomic", "selenium", "langgraph"}
    all_real = all(
        (out.get(k, {}) or {}).get("backend") in real_backends
        for k in ("slm", "embedder", "selenium", "langgraph")
    )
    out["all_real"] = all_real
    return out


# ---------------------------------------------------------------------------
# W11b / §8D.12 — Foundation fixture bootstrap
# ---------------------------------------------------------------------------

@router.post("/foundation/ensure")
def ensure_fixtures(workspace_id: str = ""):
    """Idempotently create Database + WebBrowser foundation fixtures."""
    try:
        from backend.services.foundation_fixtures import ensure_foundation_fixtures
        from backend.services.concept_index_service import get_concept_index_service
        ge = _get_graph_editor()
        ci = get_concept_index_service(broadcast=_ws_push, graph_editor=ge)
        return {"ok": True, "fixtures": ensure_foundation_fixtures(
            ge, workspace_id=workspace_id, concept_index=ci,
        )}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# UI state mirror — REST endpoints so the CLI harness (and agents) can
# drive the same selected / hovered / pinned signals the frontend emits.
# Each mutation broadcasts ``ui_state_changed`` so peer tabs reconcile.
# Read endpoint exposes the current snapshot for assertions.
# ---------------------------------------------------------------------------

class UISelectRequest(BaseModel):
    workspace_id: str = ""
    node_id: Optional[str] = None  # null clears the selection


class UIHoverRequest(BaseModel):
    workspace_id: str = ""
    node_id: Optional[str] = None  # null clears the hover


class UIPinRequest(BaseModel):
    workspace_id: str = ""
    node_id: str = ""
    # §UnifiedNodeView — freshly pinned panels start collapsed by
    # default per Mortegon §1.2. Passing collapsed=False forces an
    # immediate expand (rare; the frontend almost always leaves it
    # collapsed and only expands on subsequent hover/click).
    collapsed: bool = True
    # The screen rect where the pin should materialise — captured from
    # the hover preview at the click instant (Mortegon §1.2 step 4).
    # Schema: {top: float, left: float, width: float, height: float}.
    stick_rect: Optional[Dict[str, float]] = None


class UICollapseRequest(BaseModel):
    workspace_id: str = ""
    node_id: str = ""
    collapsed: bool = True


class UIHoverRectRequest(BaseModel):
    workspace_id: str = ""
    # Pass null/None to clear the recorded hover rect (e.g., mouseleave).
    rect: Optional[Dict[str, float]] = None


@router.post("/ui/select")
def ui_select(req: UISelectRequest):
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.select(req.workspace_id, req.node_id)
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/hover")
def ui_hover(req: UIHoverRequest):
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.hover(req.workspace_id, req.node_id)
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/pin")
def ui_pin(req: UIPinRequest):
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.node_id:
        raise HTTPException(status_code=400, detail="node_id is required")
    snap = svc.pin(
        req.workspace_id, req.node_id,
        collapsed=req.collapsed, stick_rect=req.stick_rect,
    )
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/unpin")
def ui_unpin(req: UIPinRequest):
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.node_id:
        raise HTTPException(status_code=400, detail="node_id is required")
    snap = svc.unpin(req.workspace_id, req.node_id)
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/collapse")
def ui_collapse(req: UICollapseRequest):
    """Toggle a pinned panel's collapsed flag. No-op if not pinned.

    Per Mortegon §1 + §UnifiedNodeView: passive panels stay collapsed.
    The frontend POSTs here on user-driven expand/collapse gestures so
    peer tabs + the REPL see the change.
    """
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.node_id:
        raise HTTPException(status_code=400, detail="node_id is required")
    snap = svc.set_collapsed(req.workspace_id, req.node_id, req.collapsed)
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/hover_rect")
def ui_hover_rect(req: UIHoverRectRequest):
    """Record where the hover preview is currently showing.

    The frontend posts this on every mousemove that fires the
    preview; the next pin() reads it as the stick_rect default so
    the pinned panel materialises at exactly the hover position
    (Mortegon §1.2). The REPL can also assert parity via /ui/state.
    """
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.set_hover_rect(req.workspace_id, req.rect)
    return {"ok": True, "state": snap.to_dict()}


@router.get("/ui/state")
def ui_state(workspace_id: str = ""):
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    return {"ok": True, "state": svc.get_state(workspace_id).to_dict()}


@router.get("/snapshots/{snapshot_id}/replay")
def snapshot_replay(snapshot_id: int, since: int = 0):
    """§18.1 verification tap — return frames recorded for a snapshot
    WS since ``since`` (inclusive of ``since+1``).

    The replay buffer is the source-of-truth for what ``on_stream``
    emitted, regardless of WS-subscription timing. The
    ``scan-streaming-routes-to-workspace-ws`` env-scenario uses this
    to assert workspace_id-injection on the done frame without
    depending on a flaky-bootstrap workspace WS subscription.
    """
    try:
        frames = _ws_replay.frames_since(str(snapshot_id), int(since))
    except ValueError:
        raise HTTPException(status_code=410, detail="ws_resume_expired")
    return {"ok": True, "snapshot_id": snapshot_id,
            "since": int(since), "count": len(frames),
            "frames": frames}


# §8D.2.2 — right-click compile/collapse mirror endpoints
class UICompileExpandRequest(BaseModel):
    workspace_id: str = ""
    central_id: str = ""
    children: Optional[List[str]] = None


class UICompileCollapseRequest(BaseModel):
    workspace_id: str = ""
    central_id: str = ""


@router.post("/ui/compile_expand")
def ui_compile_expand(req: UICompileExpandRequest):
    """§8D.2.2 — record that the user right-clicked a panel and it
    expanded into a simplified subgraph. Peer tabs + REPL mirror this
    state via the ui_state_changed WS broadcast."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.central_id:
        raise HTTPException(status_code=400, detail="central_id is required")
    snap = svc.compile_expand(req.workspace_id, req.central_id,
                              children=req.children)
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/compile_collapse")
def ui_compile_collapse(req: UICompileCollapseRequest):
    """§8D.2.2 — collapse a right-click expansion, restoring the panel
    to its non-expanded form. Idempotent."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.central_id:
        raise HTTPException(status_code=400, detail="central_id is required")
    snap = svc.compile_collapse(req.workspace_id, req.central_id)
    return {"ok": True, "state": snap.to_dict()}


# §8.2 / §14.2 — apparition halo focus mirror endpoints. The frontend
# POSTs the focal id + the ranked candidate list whenever the halo
# opens (or re-targets); POSTs the clear when the halo closes. The
# REPL viewer (§14.5) reads halo_focus from ui_state_changed so the
# operator sees the same focal + candidates the user sees, without a
# browser.

class UIHaloFocusRequest(BaseModel):
    workspace_id: str = ""
    focal_card_id: str = ""
    # Each candidate is the same shape ApparitionService emits:
    #   {card_id, score, pagerank, tfidf_cos, nomic_cos, name?, ...}
    # Pass None to record a focal-only update (candidates unchanged).
    candidates: Optional[List[Dict[str, Any]]] = None


class UIHaloClearRequest(BaseModel):
    workspace_id: str = ""


@router.post("/ui/halo_focus")
def ui_halo_focus(req: UIHaloFocusRequest):
    """§8.2 — frontend opens (or re-targets) the apparition halo.

    Records ``focal_card_id`` + the ranked candidates so peer surfaces
    (REPL viewer, agent perception, peer tabs) see what the user is
    seeing. Broadcasts ``ui_state_changed`` so live consoles update."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.focal_card_id:
        raise HTTPException(status_code=400, detail="focal_card_id is required")
    snap = svc.set_halo_focus(
        req.workspace_id, req.focal_card_id,
        candidates=req.candidates,
    )
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/halo_clear")
def ui_halo_clear(req: UIHaloClearRequest):
    """§8.2 — frontend closes the apparition halo (mouseleave +
    debounce, explicit dismiss, focal panel close). Idempotent."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.clear_halo_focus(req.workspace_id)
    return {"ok": True, "state": snap.to_dict()}


# §17.12 — pin chrome (drag/resize/minimise). Field-merge: each POST
# carries only the fields the gesture mutates; the setter preserves
# the prior values for unmentioned fields.

class UIPinChromeRequest(BaseModel):
    workspace_id: str = ""
    panel_id: str = ""
    top: Optional[float] = None
    left: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    minimised: Optional[bool] = None


@router.post("/ui/pin_chrome")
def ui_pin_chrome(req: UIPinChromeRequest):
    """§17.12 — merge per-panel chrome state (drag/resize/minimise).
    The setter is field-merge so gestures compose naturally."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.panel_id:
        raise HTTPException(status_code=400, detail="panel_id is required")
    snap = svc.set_pin_chrome(
        req.workspace_id, req.panel_id,
        top=req.top, left=req.left,
        width=req.width, height=req.height,
        minimised=req.minimised,
    )
    return {"ok": True, "state": snap.to_dict()}


# §17.13 — latch state (per-card slide-out toggle).

class UILatchRequest(BaseModel):
    workspace_id: str = ""
    card_id: str = ""
    # None = toggle; True = latched; False = unlatched.
    latched: Optional[bool] = None


@router.post("/ui/latch")
def ui_latch(req: UILatchRequest):
    """§17.13 / §4.4 — toggle or set the latch state of a card."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.card_id:
        raise HTTPException(status_code=400, detail="card_id is required")
    snap = svc.set_latch(
        req.workspace_id, req.card_id,
        latched=req.latched,
    )
    return {"ok": True, "state": snap.to_dict()}


# §17.14 — viewport spine (IntersectionObserver mirror).

class UIViewportSpineRequest(BaseModel):
    workspace_id: str = ""
    ordered: List[str] = []
    total: int = 0


@router.post("/ui/viewport_spine")
def ui_viewport_spine(req: UIViewportSpineRequest):
    """§17.14 / §6.4 / §8.3 — record the ordered list of chunk_ids
    currently in the scroll viewport plus the total row count."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.set_viewport_spine(
        req.workspace_id, req.ordered, req.total,
    )
    return {"ok": True, "state": snap.to_dict()}


# §17.15 — autocomplete state.

class UIAutocompleteOpenRequest(BaseModel):
    workspace_id: str = ""
    row_id: str = ""
    query: str = ""
    parent_card_id: Optional[str] = None
    # Each candidate is {card_id, name, score, ...}. Pass None to
    # keep prior candidates (the first call typically passes None,
    # the second after /api/concept_completions fetches them).
    candidates: Optional[List[Dict[str, Any]]] = None


class UIAutocompleteCloseRequest(BaseModel):
    workspace_id: str = ""
    # row_id retained for symmetry with the open call; current setter
    # is workspace-scoped (one autocomplete at a time).
    row_id: str = ""


@router.post("/ui/autocomplete")
def ui_autocomplete_open(req: UIAutocompleteOpenRequest):
    """§17.15 / §4.7 — open or update the autocomplete dropdown mirror."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.row_id:
        raise HTTPException(status_code=400, detail="row_id is required")
    snap = svc.set_autocomplete(
        req.workspace_id, req.row_id, req.query,
        parent_card_id=req.parent_card_id,
        candidates=req.candidates,
    )
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/autocomplete_clear")
def ui_autocomplete_close(req: UIAutocompleteCloseRequest):
    """§17.15 — dismiss the autocomplete dropdown mirror."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.clear_autocomplete(req.workspace_id)
    return {"ok": True, "state": snap.to_dict()}


# §4.1.1 — click-to-edit-then-Enter field state mirror.

class UIEditOpenRequest(BaseModel):
    workspace_id: str = ""
    card_id: str = ""
    field_path: str = ""
    value_so_far: str = ""


class UIEditCloseRequest(BaseModel):
    workspace_id: str = ""


@router.post("/ui/edit_open")
def ui_edit_open(req: UIEditOpenRequest):
    """§4.1.1 / §1.1 Imaginary — record that a pure-print field has
    been clicked open for editing. Peer surfaces see what is being
    edited in real time."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.card_id:
        raise HTTPException(status_code=400, detail="card_id is required")
    if not req.field_path:
        raise HTTPException(status_code=400, detail="field_path is required")
    snap = svc.set_editing_field(
        req.workspace_id, req.card_id, req.field_path,
        value_so_far=req.value_so_far,
    )
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/edit_close")
def ui_edit_close(req: UIEditCloseRequest):
    """§4.1.1 — commit / cancel / blur the active edit. Idempotent."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.clear_editing_field(req.workspace_id)
    return {"ok": True, "state": snap.to_dict()}


# §8.2.2 — autoregressive halo chain.

class UIHaloChainPushRequest(BaseModel):
    workspace_id: str = ""
    focal_card_id: str = ""


class UIHaloChainClearRequest(BaseModel):
    workspace_id: str = ""


@router.post("/ui/halo_chain_push")
def ui_halo_chain_push(req: UIHaloChainPushRequest):
    """§8.2.2 — append a new focal to the autoregressive halo chain."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.focal_card_id:
        raise HTTPException(status_code=400, detail="focal_card_id is required")
    snap = svc.push_halo_chain(req.workspace_id, req.focal_card_id)
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/halo_chain_clear")
def ui_halo_chain_clear(req: UIHaloChainClearRequest):
    """§8.2.2 — reset the autoregressive halo chain."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.clear_halo_chain(req.workspace_id)
    return {"ok": True, "state": snap.to_dict()}


# --- §4.6.1 signal-stream mirror -----------------------------------------


class UISignalStreamRequest(BaseModel):
    """Register or update a per-iterable card's signal-stream cursor."""
    card_id: str
    workspace_id: str = ""
    total: int = 0
    signal_index: int = 0
    signal_id: Optional[str] = None
    paused: bool = False
    # Which iterable field is streaming — "pattern_hash" for a pattern_map
    # panel, "url" for a url_set panel (pattern_map_and_url_set.md §5).
    field_path: str = ""
    # STEP-01 / D10 — the card's ordered sampled-chunk concept_id list (the
    # same ordered list the §17.14 spine mirror already stores). When
    # supplied, `signal_id` is resolved SERVER-SIDE as `ordered[signal_index]`
    # (bounded — V5) instead of trusting the caller's `signal_id`. The
    # frontend stepper (fe/stepper.mjs) and the REPL env-scenario pass this
    # when registering a stream so every subsequent advance resolves a real
    # 3D chunk id without re-supplying the list each time.
    ordered: Optional[List[str]] = None


class UISignalAdvanceRequest(BaseModel):
    """Advance the signal-stream cursor for one iterable card."""
    card_id: str
    workspace_id: str = ""
    step: int = 1
    field_path: str = ""
    # STEP-01 / D10 — optional ordered sampled-chunk list override for THIS
    # advance call; usually omitted since the list is already stored on the
    # entry by the prior set_signal_stream registration (single source).
    ordered: Optional[List[str]] = None


class UISignalStreamClearRequest(BaseModel):
    """Drop one card's entry, or all if card_id is empty."""
    workspace_id: str = ""
    card_id: str = ""


@router.post("/ui/signal_stream")
def ui_signal_stream(req: UISignalStreamRequest):
    """§4.6.1 signal-stream — set the cursor for an iterable card."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.set_signal_stream(
        req.workspace_id, req.card_id,
        total=int(req.total), signal_index=int(req.signal_index),
        signal_id=req.signal_id, paused=bool(req.paused),
        field_path=req.field_path or "", ordered=req.ordered,
    )
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/signal_advance")
def ui_signal_advance(req: UISignalAdvanceRequest):
    """§4.6.1 signal-stream — advance the cursor for one iterable card.

    Routes through ``RolloutCoordinator.advance`` (the single advance
    primitive) so every advance gains the §3.3 sample-boundary evolution-log
    diff AND the §R.7 per-sample cascade re-fire ("the cascade re-fires per
    visible signal, not once for the whole iterable" — §4.6.1).
    """
    from backend.services.rollout_coordinator import get_rollout_coordinator
    rc = get_rollout_coordinator(broadcast=_ws_push)
    snap = rc.advance(
        req.workspace_id, req.card_id, req.field_path or "",
        step=int(req.step), ordered=req.ordered,
    )
    return {"ok": True, "state": snap.to_dict()}


@router.post("/ui/signal_stream_clear")
def ui_signal_stream_clear(req: UISignalStreamClearRequest):
    """§4.6.1 signal-stream — clear one entry or all for the workspace."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.clear_signal_stream(req.workspace_id, req.card_id or None)
    return {"ok": True, "state": snap.to_dict()}


# ---------------------------------------------------------------------------
# §7.5 / RolloutCoordinator.md — play / pause / step / reset the iterated
# rollout. Thin controls over the signal-stream mirror; the per-interval
# advance cadence is frontend/REPL-driven (single-user on-device), the backend
# owns the state + the advance primitive.
# ---------------------------------------------------------------------------

class RolloutPlayRequest(BaseModel):
    card_id: str
    field_path: str = ""
    workspace_id: str = ""
    interval_ms: int = 1000


class RolloutControlRequest(BaseModel):
    """pause / step / reset — card_id + field_path identify the rollout."""
    card_id: str
    field_path: str = ""
    workspace_id: str = ""
    node_id: Optional[str] = None


@router.post("/rollout/play")
def rollout_play(req: RolloutPlayRequest):
    """§7.5 — mark the rollout playing (paused=False) + emit rollout_resumed."""
    from backend.services.rollout_coordinator import get_rollout_coordinator
    rc = get_rollout_coordinator(broadcast=_ws_push)
    snap = rc.play(req.workspace_id, req.card_id, req.field_path or "",
                   interval_ms=int(req.interval_ms or 1000))
    return {"ok": True, "state": snap.to_dict(), "rollout_state": snap.rollout_state}


@router.post("/rollout/pause")
def rollout_pause(req: RolloutControlRequest):
    """§7.5 — halt at the current sample (paused=True) + emit rollout_paused."""
    from backend.services.rollout_coordinator import get_rollout_coordinator
    rc = get_rollout_coordinator(broadcast=_ws_push)
    snap = rc.pause(req.workspace_id, req.card_id, req.field_path or "",
                    node_id=req.node_id)
    return {"ok": True, "state": snap.to_dict(), "rollout_state": snap.rollout_state}


@router.post("/rollout/step")
def rollout_step(req: RolloutControlRequest):
    """§7.5 — one advance, then re-pause."""
    from backend.services.rollout_coordinator import get_rollout_coordinator
    rc = get_rollout_coordinator(broadcast=_ws_push)
    snap = rc.step(req.workspace_id, req.card_id, req.field_path or "")
    return {"ok": True, "state": snap.to_dict(), "rollout_state": snap.rollout_state}


@router.post("/ui/signal_reset")
def ui_signal_reset(req: RolloutControlRequest):
    """§7.5 — return the rollout cursor to 0 (signal_index=0, paused)."""
    from backend.services.rollout_coordinator import get_rollout_coordinator
    rc = get_rollout_coordinator(broadcast=_ws_push)
    snap = rc.reset(req.workspace_id, req.card_id, req.field_path or "")
    return {"ok": True, "state": snap.to_dict(), "rollout_state": snap.rollout_state}


# ---------------------------------------------------------------------------
# §6.6.4 / §7.8 — Compute-graph projector overlay (bisector node + readout
# perimeter + UMAP-independent link network)
# ---------------------------------------------------------------------------

class ComputeGraphLayoutRequest(BaseModel):
    """§6.6.4 — request the compute-graph projector overlay for the
    ``{ref}``-connected graph that ``focal_id`` belongs to.

    ``stream=True`` (§7.8.3) emits the perimeter as **per-readout deltas**
    (one ``compute_graph_layout`` frame per readout, monotone ``settle_seq``,
    no barrier batch §18.34) instead of one snapshot frame."""
    focal_id: str
    workspace_id: str = ""
    stream: bool = False


@router.post("/compute_graph/layout")
def compute_graph_layout(req: ComputeGraphLayoutRequest):
    """§6.6.4 / §7.8.2-3 — compute + broadcast the compute-graph projector
    overlay for ``focal_id``'s ``{ref}``-connected component:

      * the **readout perimeter** (``readout_nodes`` §7.8.2) and the
        **input sources** (``input_nodes`` §7.8.1);
      * the single collapsed **bisector node**, placed on the linear
        bisector between the input 6D-UMAP centroid and the
        (dynamically-recomputed) readout centroid
        (``place_compute_graph_node`` P.10) — neither centroid is rendered;
      * the **UMAP-independent link network** (``compute_projector_links``
        P.8/P.9) — plain coordinate-free links, never folded into
        ``umap_canonical`` (anti-goal §18.34).

    Dual-routed (anti-goal §18.1): the ``compute_graph_layout`` frame is
    pushed on the workspace WS AND returned in the REST body so the REPL,
    peer tabs, and the caller all observe one overlay. ``graph_id`` is
    **component-invariant** (``graph_component(...)[0]``) so any focal of
    the same graph addresses the same projector node + ``settle_seq``
    series.
    """
    from backend.services.conceptual_compute import (
        readout_nodes, input_nodes, graph_component, stream_readout_deltas,
    )
    from backend.services.layout_service import get_layout_service
    from backend.api.ws_frames import build_compute_graph_layout

    ge = _get_graph_editor()
    ws = req.workspace_id or ""
    focal = req.focal_id or ""

    component = graph_component(focal, graph_editor=ge, workspace_id=ws)
    graph_id = component[0] if component else focal
    readouts = readout_nodes(focal, graph_editor=ge, workspace_id=ws)
    inputs = input_nodes(focal, graph_editor=ge, workspace_id=ws)

    layout = get_layout_service(broadcast=_ws_push)

    if req.stream:
        # §7.8.3 — stream the perimeter as PER-READOUT deltas (one frame per
        # readout, monotone settle_seq, no barrier batch §18.34) rather than a
        # single snapshot frame. Each delta is pushed on the workspace WS.
        deltas = stream_readout_deltas(
            focal, graph_editor=ge, layout_service=layout,
            workspace_id=ws, broadcast=_ws_push,
        )
        return {
            "ok": True,
            "graph_id": graph_id,
            "inputs": inputs,
            "readouts": readouts,
            "streamed": True,
            "delta_count": len(deltas),
            "deltas": deltas,
        }

    placement = layout.place_compute_graph_node(ws, graph_id, inputs, readouts)
    links = layout.compute_projector_links(
        ws, graph_id,
        input_ids=inputs, readout_ids=readouts,
        url_sample_map={},   # populated by inverse-lookup (§7.8.1) — pending
    )

    # Seat each settled readout on its current perimeter coordinate (if the
    # layout frame carries one). The coord rides THIS frame, not a
    # chunk_replaced (§7.8.3) — the projector re-places without a refit.
    # §R.4 — each readout ships as its RENDERED PANEL (name + the §8D.20
    # clean-text tree), so the 3D mirror projects the perimeter as panels;
    # hidden-state nodes never appear here (readout_nodes excludes any node
    # with succeeding links).
    from backend.services.conceptual_compute import readout_panel_payload
    frame_obj = layout.get_frame(ws)
    coords = frame_obj.coords if frame_obj is not None else {}
    readout_payload: List[Dict[str, Any]] = [
        readout_panel_payload(rid, coords.get(rid), graph_editor=ge)
        for rid in readouts
    ]

    frame = build_compute_graph_layout(
        workspace_id=ws, placement=placement,
        readouts=readout_payload, links=links,
    )
    _ws_push(0, frame)

    return {
        "ok": True,
        "graph_id": graph_id,
        "inputs": inputs,
        "readouts": readouts,
        "overlay": frame,
    }


class OntologyLayoutRequest(BaseModel):
    """§R.2 — request the full-ontology 6D projection for a workspace."""
    workspace_id: str = ""


@router.post("/ontology/layout")
def ontology_layout(req: OntologyLayoutRequest):
    """§R.2 — project the FULL database ontology into the 3D UMAP GUI.

    Every workspace ConceptNode — the foundation fixtures, the python-
    native functional-object trees (Database / WebBrowser / Agent /
    Editor materialisations), user-authored concepts, compiled-from-scans
    — gets a 6D (xyz+HSV) coordinate from its nomic vector (the concept-
    side sibling pipeline, §2.3), sitting alongside the scanned-chunk
    field. Vectorless concepts ride the §6.1 hash placeholder until the
    next recompute. Dual-routed (§18.1): the ``ontology_layout`` frame is
    pushed on the workspace WS AND returned in the REST body, with the
    coordinate-free one-edge-table adjacency for the link rendering.
    """
    from backend.services.layout_service import get_layout_service
    from backend.services.concept_index_service import get_concept_index_service

    ge = _get_graph_editor()
    ci = get_concept_index_service(broadcast=_ws_push, graph_editor=ge)
    layout = get_layout_service(broadcast=_ws_push)
    out = layout.recompute_ontology(
        req.workspace_id or "",
        concept_index=ci,
        graph_editor=ge,
        broadcast_frame=True,
    )
    return {"ok": True, "workspace_id": req.workspace_id or "", **out}


class UINodeFoldRequest(BaseModel):
    """§7.3.4 — inline node-fold toggle (right-click a {ref} token)."""
    card_id: str
    field_path: str
    expanded: bool = True
    workspace_id: str = ""


@router.post("/ui/node_fold")
def ui_node_fold(req: UINodeFoldRequest):
    """§7.3.4 / object_exploration — toggle an inline node-fold path open/closed
    (rank-1 reveal of a {ref} token without leaving the panel)."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    snap = svc.set_node_fold(
        req.workspace_id, req.card_id, req.field_path, expanded=bool(req.expanded),
    )
    return {"ok": True, "state": snap.to_dict(),
            "node_fold_state": snap.node_fold_state}


class UIUrlVisibilityRequest(BaseModel):
    workspace_id: str = ""
    url: str = ""
    collapsed: bool = True


class UIRegisterBillboardUrlRequest(BaseModel):
    workspace_id: str = ""
    billboard_id: str = ""
    url: str = ""


@router.post("/ui/url_visibility")
def ui_url_visibility(req: UIUrlVisibilityRequest):
    """Toggle a URL's collapsed flag. Emits
    ``ui_url_visibility_changed`` with the list of affected pinned
    billboards so the animate loop + peer tabs + the REPL drain all
    see the cascade (Mortegon §5)."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.url:
        raise HTTPException(status_code=400, detail="url is required")
    snap = svc.set_url_collapsed(req.workspace_id, req.url, req.collapsed)
    return {"ok": True, "state": snap.to_dict()}


class UIDominanceCollapseRequest(BaseModel):
    """§6.6.5 / §7.3.5 — generalized rank-dominance collapse (Q.3-Q.5)."""
    workspace_id: str = ""
    node_id: str = ""
    collapsed: bool = True


@router.post("/ui/dominance_collapse")
def ui_dominance_collapse(req: UIDominanceCollapseRequest):
    """§6.6.5 (3D) / §7.3.5 (2D) — the generalized rank-dominance
    collapse/expand gesture (Q.3-Q.5).

    Right-clicking a *dominator* node folds its dominated set and — in the
    3D projector — hides every other node (the isolate, Q.3); a second
    right-click re-expands. The dominated set (``folded_set``) is the
    node's rank-dominance reachability over the ConceptEdge graph + the
    chunk-url association (``rank_dominance.py``, §8.1.2 — the *same* graph
    PageRank runs over, Q.6); ``hidden_set`` is every other visible node.
    Distinct from ``/ui/url_visibility`` (§18.12): different gesture,
    surface, and mirror field.
    """
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.node_id:
        raise HTTPException(status_code=400, detail="node_id is required")

    hidden_set: list = []
    folded_set: list = []
    if req.collapsed:
        from backend.services.rank_dominance import (
            build_chunk_url_map, compute_dominance_sets,
        )
        from backend.services.layout_service import get_layout_service
        from backend.services.global_tfidf_store import get_default_store

        layout = get_layout_service(broadcast=_ws_push)
        frame = None
        try:
            frame = layout.get_frame(req.workspace_id)  # type: ignore[attr-defined]
        except Exception:
            frame = None
        coords_keys = list(getattr(frame, "coords", {}) or {}) if frame else []
        url_root_keys = list(getattr(frame, "url_roots", {}) or {}) if frame else []

        try:
            store = get_default_store()
            chunk_url_map = build_chunk_url_map(store)
        except Exception:
            chunk_url_map = {}

        ge = _get_graph_editor()
        # Use the SAME Kuzu ConceptEdge graph PageRank traverses (§8.1.2,
        # the one-edge-table invariant) — not the in-memory _edges list.
        try:
            edges = ge.list_concept_edges(workspace_id=req.workspace_id, limit=50000)
        except Exception:
            edges = []

        folded_set, hidden_set = compute_dominance_sets(
            req.node_id,
            coords_keys=coords_keys,
            url_root_keys=url_root_keys,
            chunk_url_map=chunk_url_map,
            edges=edges,
        )

    snap = svc.set_dominance_collapse(
        req.workspace_id, req.node_id, bool(req.collapsed),
        hidden_set=hidden_set, folded_set=folded_set,
    )
    return {"ok": True, "state": snap.to_dict(),
            "dominance_collapse": snap.dominance_collapse}


@router.post("/ui/register_billboard_url")
def ui_register_billboard_url(req: UIRegisterBillboardUrlRequest):
    """Frontend tells the mirror which URL spawned a pinned billboard.
    The URL-collapse cascade reads this to resolve affected ids."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    if not req.billboard_id:
        raise HTTPException(status_code=400, detail="billboard_id is required")
    snap = svc.register_billboard_url(
        req.workspace_id, req.billboard_id, req.url,
    )
    return {"ok": True, "state": snap.to_dict()}


@router.get("/ui/hidden_billboards")
def ui_hidden_billboards(workspace_id: str = ""):
    """Return the ids of pinned billboards currently hidden because
    their source URL is collapsed (Mortegon §5 cascade contract)."""
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    return {
        "ok":     True,
        "hidden": svc.get_hidden_billboards(workspace_id),
    }


@router.get("/ui/node_state/{node_id}")
def ui_node_state(node_id: str, workspace_id: str = ""):
    """One-shot ``{state, collapsed, pinned, hovered}`` for a node.

    ``state`` ∈ {``hovered`` | ``sticky`` | ``sticky+hovered`` |
    ``passive``} per the §UnifiedNodeView model. The REPL uses this
    to assert hover/click gestures produced the expected presentation
    state without screen-scraping the browser.
    """
    from backend.services.ui_state_service import get_ui_state_service
    svc = get_ui_state_service(broadcast=_ws_push)
    return {"ok": True, **svc.view_state(workspace_id, node_id)}


# ---------------------------------------------------------------------------
# UI telemetry — frontend → backend channel for MutationObserver reports.
# The frontend POSTs ``{kind, target_id?, count?, extra?}`` whenever a
# tracked DOM area changes; the CLI (or an agent) drains via GET so the
# console sees what's actually rendered on screen without screen-scraping.
# ---------------------------------------------------------------------------

class UITelemetryRequest(BaseModel):
    workspace_id: str = ""
    kind: str = ""
    target_id: Optional[str] = None
    count: Optional[int] = None
    extra: Dict[str, Any] = {}


@router.post("/ui/telemetry")
def ui_telemetry_push(req: UITelemetryRequest):
    """Frontend-side MutationObserver pushes one report here.

    Backend stores it in a per-workspace ring buffer + broadcasts a
    ``ui_telemetry`` WS frame so live consoles see it immediately.
    """
    if not req.kind:
        raise HTTPException(status_code=400, detail="kind is required")
    from backend.services.ui_telemetry_service import get_ui_telemetry_service
    svc = get_ui_telemetry_service(broadcast=_ws_push)
    entry = svc.push(
        req.workspace_id,
        kind=req.kind,
        target_id=req.target_id,
        count=req.count,
        extra=req.extra or {},
    )
    return {"ok": True, "entry": entry.to_dict()}


@router.get("/ui/telemetry")
def ui_telemetry_drain(workspace_id: str = "", since_seq: int = 0,
                       limit: int = 256):
    """Drain (non-destructively) every telemetry entry with seq >
    ``since_seq``. CLI passes the last seq it saw to paginate.
    """
    from backend.services.ui_telemetry_service import get_ui_telemetry_service
    svc = get_ui_telemetry_service(broadcast=_ws_push)
    entries = svc.drain(workspace_id, since_seq=int(since_seq), limit=int(limit))
    return {
        "ok":           True,
        "workspace_id": workspace_id or "_default",
        "head_seq":     svc.head_seq(workspace_id),
        "count":        len(entries),
        "entries":      [e.to_dict() for e in entries],
    }


# ---------------------------------------------------------------------------
# spine_delta REST mirror — WS handler at /api/ws/workspace already handles
# incoming spine_delta frames from the frontend, but the CLI harness has
# no WS write surface, so without this mirror the agent's
# zone_of_influence is unreachable from terminal-based testing.
# ---------------------------------------------------------------------------

class SpineDeltaRequest(BaseModel):
    workspace_id: str = ""
    popped: List[str] = []
    folded: List[str] = []


@router.post("/spine_delta")
def spine_delta(req: SpineDeltaRequest):
    """REST mirror of the WS-side spine_delta consumer. Writes the
    delta to every active agent's zone_of_influence so a running
    meta-cognition node sees what the simulated user is attending to
    (§8D.27).
    """
    try:
        from backend.services.agent_runtime import (
            apply_spine_delta_to_active_agents,
        )
        apply_spine_delta_to_active_agents(
            graph_editor=_get_graph_editor(),
            workspace_id=req.workspace_id,
            popped=list(req.popped or []),
            folded=list(req.folded or []),
            push_fn=_ws_push,
        )
        return {"ok": True, "popped": len(req.popped or []),
                "folded": len(req.folded or [])}
    except Exception as e:
        logger.warning("spine_delta REST apply failed: %s", e)
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# W24 / §8C.8, §8D.32 — Agent review queue REST endpoints
# ---------------------------------------------------------------------------

@router.get("/agent/reviews")
def list_agent_reviews(workspace_id: Optional[str] = None):
    """List pending RequestUserReviewAction entries (§8C.8)."""
    from backend.services.review_queue import get_review_queue
    entries = get_review_queue().list_pending(workspace_id=workspace_id)
    return {"entries": [e.to_dict() for e in entries]}


class ReviewResolveRequest(BaseModel):
    review_id: str
    decision: str = "accepted"   # accepted | dismissed


@router.post("/agent/reviews/resolve")
def resolve_agent_review(req: ReviewResolveRequest):
    from backend.services.review_queue import get_review_queue
    e = get_review_queue().resolve(req.review_id, decision=req.decision)
    if e is None:
        raise HTTPException(status_code=404, detail=f"review {req.review_id} not found")
    return {"ok": True, "entry": e.to_dict()}


# ---------------------------------------------------------------------------
# C4 / §8D.44 — Backing-pointer registry invocation
# ---------------------------------------------------------------------------

class InvokeBackingRequest(BaseModel):
    """Invoke a concept node's backing pointer directly."""
    concept_id: str = ""
    handle: str = ""  # if blank, look up from concept's backing_pointer
    kwargs: Dict[str, Any] = {}


@router.post("/backing/invoke")
def invoke_backing(req: InvokeBackingRequest):
    """§8D.44 — Resolve and invoke a concept node's backing pointer.

    Either supply ``handle`` directly OR ``concept_id`` (we look up
    the node's backing_pointer). Returns ``{ok, result?, error?}``.
    """
    from backend.services.backing_registry import get_backing_registry
    reg = get_backing_registry()
    handle = req.handle or ""
    if not handle and req.concept_id:
        ge = _get_graph_editor()
        node = ge.get_concept(req.concept_id)
        if node:
            handle = node.backing_pointer
    if not handle:
        return {"ok": False, "error": "no handle provided and no concept_id resolved"}
    return reg.invoke(handle, **(req.kwargs or {}))


# ---------------------------------------------------------------------------
# W10 / §8D.27 — Agent tick endpoint
# ---------------------------------------------------------------------------

class AgentTickRequest(BaseModel):
    """One-tick fire for the meta-cognition node bound to a parameter card."""
    parameter_card_id: str = ""
    workspace_id: str = ""


class AgentSpawnRequest(BaseModel):
    """Create a parameter card + visible body subgraph (§8D.27).

    If ``parameter_card_id`` is given, attach a body subgraph to that
    existing card (idempotent — re-running returns the existing trio).
    Otherwise create the parameter card first with the given ``goal``.

    ``idempotency_key`` — optional UUID; backend dedupes by key over
    ``settings.idempotency_ttl_sec`` so retries don't create N
    duplicate agents.
    """
    workspace_id: str = ""
    parameter_card_id: str = ""
    goal: str = ""
    name: str = ""
    idempotency_key: Optional[str] = None


class AgentForkRequest(BaseModel):
    """Fork an existing agent — clones the parameter card + body trio
    under a new parameter card id (§8D.32.3)."""
    source_parameter_card_id: str
    workspace_id: str = ""
    new_name: str = ""
    idempotency_key: Optional[str] = None


@router.post("/agent/fork")
def agent_fork(req: AgentForkRequest):
    """§8D.32.3 — drag-clone an agent's subgraph as a new sibling.

    Reads the source's parameter / perception / transformer / emitter
    cards, spawns a fresh body subgraph for a new parameter card,
    and copies the source's data blocks into the new cards so any
    user-customised configuration (prompt template, emitter filter,
    perception toggles) is preserved in the fork. The fork starts
    on manual mode (``cascade_enabled=false``, ``paused=false``) and
    its ``step_index`` resets to 0.
    """
    if not req.source_parameter_card_id:
        raise HTTPException(status_code=400, detail="source_parameter_card_id required")
    cached = _idempotency_lookup(
        req.workspace_id, f"fork:{req.source_parameter_card_id}",
        req.idempotency_key,
    )
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    from backend.services.agent_runtime import fork_agent_body_subgraph
    response = fork_agent_body_subgraph(
        graph_editor=ge,
        source_parameter_card_id=req.source_parameter_card_id,
        workspace_id=req.workspace_id or "",
        new_name=req.new_name or "",
        push_fn=_ws_push,
    )
    _idempotency_store(
        req.workspace_id, f"fork:{req.source_parameter_card_id}",
        req.idempotency_key, response,
    )
    return response


# ---------------------------------------------------------------------------
# §9.5.1 four-fixture primitives (docs/code_constraints/api_routes.md §1.5).
#
# Each primary-function endpoint maps 1:1 to the public method of its
# anchoring foundation fixture so the user (REPL / GUI) and the agent
# emitter share one canonical surface (§12.6.1 entanglement). Endpoints
# are idempotent on the optional ``idempotency_key`` body field per
# §1.1 must-hold (anti-goal: retry storm).
# ---------------------------------------------------------------------------


class AgentMetaPromptRequest(BaseModel):
    """Set the agent fixture's *meta-prompt* (system / role directive).

    Per ``docs/object_model/Agent.md`` the three primitives compose: the
    meta-prompt sets context, the prompt issues the immediate instruction,
    and ``output`` fires the SLM. Meta-prompt is held in-process on the
    process-singleton agent runtime until the next ``output`` consumes it.
    """
    text: str = ""
    workspace_id: str = ""
    idempotency_key: Optional[str] = None


class AgentPromptRequest(BaseModel):
    """Queue the immediate prompt text for the next ``output`` fire."""
    text: str = ""
    workspace_id: str = ""
    idempotency_key: Optional[str] = None


class AgentOutputRequest(BaseModel):
    """Fire the SLM with the queued meta-prompt + prompt.

    Optional ``output_schema`` is a JSON-shaped pydantic-style schema;
    if set, the SLM returns a typed dict; if absent, free text. Returns
    ``{"text": str, "structured": dict|None, "model": str, "backend":
    "gpt4all"|"stub"}``. Field is named ``output_schema`` rather than
    ``schema`` to avoid shadowing Pydantic's reserved ``schema`` attr.
    """
    output_schema: Optional[Dict[str, Any]] = None
    workspace_id: str = ""
    idempotency_key: Optional[str] = None


# Tiny process-singleton buffer for meta_prompt + prompt staging. Per
# workspace so concurrent users don't collide; cleared on consume.
_AGENT_PROMPT_BUFFER: Dict[str, Dict[str, str]] = {}


def _agent_buffer(workspace_id: str) -> Dict[str, str]:
    ws = workspace_id or "_default"
    if ws not in _AGENT_PROMPT_BUFFER:
        _AGENT_PROMPT_BUFFER[ws] = {"meta_prompt": "", "prompt": ""}
    return _AGENT_PROMPT_BUFFER[ws]


@router.post("/agent/meta_prompt")
def agent_meta_prompt(req: AgentMetaPromptRequest):
    """§9.5.1 Agent.meta_prompt(text) — set the system / role directive."""
    cached = _idempotency_lookup(req.workspace_id, "agent:meta_prompt",
                                  req.idempotency_key)
    if cached is not None:
        return cached
    buf = _agent_buffer(req.workspace_id)
    buf["meta_prompt"] = req.text or ""
    response = {"ok": True, "workspace_id": req.workspace_id,
                "meta_prompt_chars": len(buf["meta_prompt"])}
    _idempotency_store(req.workspace_id, "agent:meta_prompt",
                       req.idempotency_key, response)
    return response


@router.post("/agent/prompt")
def agent_prompt(req: AgentPromptRequest):
    """§9.5.1 Agent.prompt(text) — queue the immediate user-style prompt."""
    cached = _idempotency_lookup(req.workspace_id, "agent:prompt",
                                  req.idempotency_key)
    if cached is not None:
        return cached
    buf = _agent_buffer(req.workspace_id)
    buf["prompt"] = req.text or ""
    response = {"ok": True, "workspace_id": req.workspace_id,
                "prompt_chars": len(buf["prompt"])}
    _idempotency_store(req.workspace_id, "agent:prompt",
                       req.idempotency_key, response)
    return response


@router.post("/agent/output")
def agent_output(req: AgentOutputRequest):
    """§9.5.1 Agent.output(schema?) — fire the SLM with buffered prompts.

    Consumes the meta_prompt + prompt buffer for the workspace.
    Free-text mode by default; passes schema to ``generate_structured``
    when provided. Real GPT4All Nous Hermes Mistral 2 DPO in production;
    stub only if ``WFH_FAKE_SLM=1``.
    """
    cached = _idempotency_lookup(req.workspace_id, "agent:output",
                                  req.idempotency_key)
    if cached is not None:
        return cached
    buf = _agent_buffer(req.workspace_id)
    meta = buf.get("meta_prompt", "")
    prompt = buf.get("prompt", "")
    from backend.services.slm_client import SLMClient
    slm = SLMClient()
    try:
        if req.output_schema is not None:
            structured = slm.generate_structured(prompt, meta, req.output_schema)
            text = json.dumps(structured)
        else:
            text = slm.generate_text(prompt, meta)
            structured = None
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SLM error: {e}")
    # Consume the buffer so the next call starts fresh.
    buf["meta_prompt"] = ""
    buf["prompt"] = ""
    response = {
        "ok": True,
        "text": text,
        "structured": structured,
        "status": slm.status(),
    }
    _idempotency_store(req.workspace_id, "agent:output",
                       req.idempotency_key, response)
    return response


# --- Database.* primitives ------------------------------------------------


class DatabaseCypherRequest(BaseModel):
    """§9.5.1 Database.cypher(query) — direct cypher passthrough."""
    query: str = ""
    workspace_id: str = ""


class DatabaseConceptRequest(BaseModel):
    """§9.5.1 Database.concept(node_id [or list]) — rank-1 KG walk.

    Returns the immediate neighbourhood of each node (outgoing +
    incoming ConceptEdges) so the iterator can stream signal-by-signal
    when called with a list (§4.6.1 signal-stream constraint).
    """
    node_id: Optional[str] = None
    node_ids: Optional[List[str]] = None
    workspace_id: str = ""


@router.post("/database/cypher")
def database_cypher(req: DatabaseCypherRequest):
    """§9.5.1 Database.cypher — pass a cypher query to Kuzu directly.

    Returns ``{"ok": bool, "rows": [...], "error": str?}``. Raw Kuzu
    output; the caller handles pagination + display.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query required")
    ge = _get_graph_editor()
    db = getattr(ge, "_db_conn", None)
    if db is None:
        return {"ok": False, "rows": [], "error": "no Kuzu connection"}
    try:
        result = db.execute(req.query)
        rows: List[Dict[str, Any]] = []
        try:
            # Kuzu .execute returns a QueryResult; iterate rows.
            cols = list(result.get_column_names()) if hasattr(result, "get_column_names") else []
            while hasattr(result, "has_next") and result.has_next():
                row_vals = result.get_next() if hasattr(result, "get_next") else None
                if row_vals is None:
                    break
                rows.append(dict(zip(cols, row_vals)) if cols else {"row": row_vals})
        except Exception as e:
            return {"ok": False, "rows": rows, "error": str(e)}
        return {"ok": True, "rows": rows}
    except Exception as e:
        return {"ok": False, "rows": [], "error": str(e)}


@router.post("/database/concept")
def database_concept(req: DatabaseConceptRequest):
    """§9.5.1 Database.concept — rank-1 KG walk for one or many nodes.

    Returns a list of neighbourhood records keyed by input node id.
    Each record carries the node itself plus its outgoing + incoming
    ConceptEdges (resolved targets included for fast rendering).
    """
    ids: List[str] = []
    if req.node_ids:
        ids = [s for s in req.node_ids if s]
    elif req.node_id:
        ids = [req.node_id]
    if not ids:
        raise HTTPException(status_code=400,
                            detail="node_id or node_ids required")
    ge = _get_graph_editor()
    out: List[Dict[str, Any]] = []
    for nid in ids:
        node = ge.get_concept(nid)
        if node is None:
            out.append({"node_id": nid, "found": False, "edges": []})
            continue
        # Use the existing get_edges helper for the rank-1 walk.
        try:
            edges = ge.get_edges(nid) or []
        except Exception:
            edges = []
        out.append({
            "node_id": nid,
            "found": True,
            "node": {
                "concept_id": node.concept_id,
                "name": node.name,
                "description": node.description,
                "data": node.data,
                "rendering": node.rendering,
                "provenance": node.provenance,
                "workspace_id": node.workspace_id,
            },
            "edges": edges,
        })
    return {"ok": True, "results": out, "count": len(out)}


# --- WebBrowser.scan -------------------------------------------------------


class WebBrowserScanRequest(BaseModel):
    """§9.5.1 WebBrowser.scan(url, query?) — live shadow-DOM scan.

    The query, if present, is forwarded to the URL's search form (when
    one is detected) so retrieval rows surface for that query. Streams
    chunks via the workspace WS as the scan proceeds (§17.1 + §18.1).
    """
    url: str = ""
    query: str = ""
    samples: int = 8
    duration_s: int = 0          # §15.10 time-box (Q.2): 0 ⇒ sample-bounded; >0 ⇒ scan for N wall-clock seconds
    workspace_id: str = ""


@router.post("/web_browser/scan")
def web_browser_scan(req: WebBrowserScanRequest,
                     background_tasks: BackgroundTasks):
    """§9.5.1 WebBrowser.scan — canonical scan-trigger endpoint.

    Thin wrapper over the existing ``trigger_snapshot`` path so the
    four-fixture API surface is symmetric. The legacy ``/api/snapshot``
    endpoint still works for older clients; new code uses this one.

    ``duration_s`` is the §15.10 timed-scan time-box (Q.2): it maps to
    ``trigger_snapshot``'s ``max_duration`` (→ ``mapper.snapshot``). 0
    means sample-bounded (legacy); >0 scans for that many wall-clock
    seconds then finalises.
    """
    if not req.url:
        raise HTTPException(status_code=400, detail="url required")
    # Defer to the legacy trigger_snapshot path. trigger_snapshot owns
    # the background scan task; query/samples are consumed by the
    # pipeline's search-input detection + pagination, duration_s by the
    # wall-clock time-box.
    return trigger_snapshot(
        background_tasks,
        url=req.url,
        workspace_id=req.workspace_id,
        max_duration=int(req.duration_s or 0),
    )


# --- Editor.* primitives ---------------------------------------------------


class EditorCreateRequest(BaseModel):
    """§9.5.1 Editor.create — new ConceptNode through the lifecycle."""
    name: str = ""
    description: str = ""
    data: str = ""
    workspace_id: str = ""
    idempotency_key: Optional[str] = None


class EditorLinkRequest(BaseModel):
    """§9.5.1 Editor.link — new ConceptEdge through the lifecycle.

    ``edge_type`` defaults to ``RELATES_TO`` which is the canonical
    EDGE_TYPES entry from graph_editor.py. Other valid types include
    ``ANNOTATES``, ``IS_A``, ``HAS_A``, ``PART_OF``, ``DERIVED_FROM``,
    ``INCLUDES``, ``SIMILAR_TO``, ``CLASSIFIES``.

    ``inherit_types`` (Phase 7 EXPLORE-03 / N.4, default False so existing
    callers are byte-for-byte unaffected): when True, AFTER the edge is
    created the target node inherits the source node's I/O types + object
    model — the source's outgoing ``OBJECT_HAS_PROPERTY`` /
    ``OBJECT_HAS_FUNCTION`` / ``FUNCTION_INPUT_TYPE`` / ``FUNCTION_OUTPUT_TYPE``
    edges (the SAME four-edge materialiser vocabulary ``next_rank`` reads,
    see ``_NEXT_RANK_EDGE_TYPES``) are mirrored onto the target as a single
    synchronous side-effect of this same request, fanned through the
    existing ``apply_edge_create_lifecycle`` dispatcher (RESEARCH Open-Q3:
    one request, one lifecycle event — never a frontend-orchestrated
    two-step).
    """
    source_id: str
    target_id: str
    edge_type: str = "RELATES_TO"
    workspace_id: str = ""
    idempotency_key: Optional[str] = None
    inherit_types: bool = False


class EditorOverwriteRequest(BaseModel):
    """§9.5.1 Editor.overwrite — single-field update."""
    concept_id: str
    field: str
    value: Any = ""
    workspace_id: str = ""
    idempotency_key: Optional[str] = None


class EditorDeleteRequest(BaseModel):
    """§9.5.1 Editor.delete — cascade-aware tombstone."""
    concept_id: str
    workspace_id: str = ""
    idempotency_key: Optional[str] = None


@router.post("/editor/create")
def editor_create(req: EditorCreateRequest):
    """§9.5.1 Editor.create — symmetric surface for user + agent.

    Goes through ``apply_update_lifecycle`` so WS / index / evolution
    log all fire identically whether the caller is a panel gesture or
    an agent emit-action (§12.6.1 entanglement).
    """
    cached = _idempotency_lookup(req.workspace_id, f"editor:create:{req.name}",
                                  req.idempotency_key)
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    node = ge.create_concept(
        name=req.name or "untitled",
        description=req.description or "",
        data=req.data or "",
        provenance="user-authored",
        workspace_id=req.workspace_id or "",
    )
    # §3.1 / §12.6.1 — fire the fan-out (WS broadcast + ConceptIndex upsert +
    # output-projection schedule + EvolutionLog + cascade nudge) so the Editor
    # primitive is symmetric with the panel-gesture path, exactly as the
    # docstring promises. (Was calling create_concept raw, skipping all of it.)
    if node is not None:
        _apply_update_lifecycle(
            node, ge, pre_dict=None, node_dict=_concept_to_dict(node),
            actor="editor",
        )
    response = {"ok": True, "concept_id": node.concept_id if node else None,
                "name": req.name}
    _idempotency_store(req.workspace_id, f"editor:create:{req.name}",
                       req.idempotency_key, response)
    return response


@router.post("/editor/link")
def editor_link(req: EditorLinkRequest):
    """§9.5.1 Editor.link — new ConceptEdge through the lifecycle.

    Routes through ``create_concept_edge`` (the ConceptEdge-table writer) +
    ``apply_edge_create_lifecycle`` — the SAME path as ``/concept_edges`` — so
    the §3.1 edge fan-out (WS broadcast for both endpoints + ConceptIndex
    PageRank refit + EvolutionLog "link") fires identically whether the caller
    is a panel gesture or an agent emit-action (§12.6.1 entanglement). The
    legacy ``create_edge`` it previously called wrote to the ontology-node edge
    list (not the ConceptEdge table) and skipped the lifecycle entirely.
    """
    cached = _idempotency_lookup(
        req.workspace_id,
        f"editor:link:{req.source_id}:{req.target_id}:{req.edge_type}",
        req.idempotency_key,
    )
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    # Phase 7 EXPLORE-03 (T-07-06 / RESEARCH Security Domain) — validate the
    # source/target pair BEFORE creating the edge so an invalid concept_id
    # still 400s; create_concept_edge itself is idempotent and raises no
    # ValueError for unknown ids, so this check is the validation that
    # preserves "invalid edges still 400" rather than silently linking
    # nonexistent nodes. Never bypassed for the inherit_types fast path.
    if ge.get_concept(req.source_id) is None or ge.get_concept(req.target_id) is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid edge: source_id={req.source_id!r} or target_id={req.target_id!r} not found",
        )
    try:
        edge = ge.create_concept_edge(
            source_id=req.source_id,
            target_id=req.target_id,
            edge_type=req.edge_type or "RELATES_TO",
            workspace_id=req.workspace_id or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    from backend.services.concept_lifecycle import apply_edge_create_lifecycle
    edge_dict = apply_edge_create_lifecycle(
        edge, ge, workspace_id=req.workspace_id or "", push_fn=_ws_push,
    )
    # Phase 7 EXPLORE-03 / N.4 — optional single synchronous I/O-type-
    # inheritance side-effect, fanned through the SAME lifecycle dispatcher
    # (RESEARCH Open-Q3: one request, one lifecycle event). Default-False
    # path above is unchanged byte-for-byte; this only runs when requested.
    inherited_edges = []
    if req.inherit_types:
        for inherited_edge in _inherit_io_types(
            ge, req.source_id, req.target_id, req.workspace_id or "",
        ):
            apply_edge_create_lifecycle(
                inherited_edge, ge, workspace_id=req.workspace_id or "", push_fn=_ws_push,
            )
            inherited_edges.append(_edge_to_dict(inherited_edge))
    response = {"ok": True, "edge": edge_dict or _edge_to_dict(edge)}
    if req.inherit_types:
        response["inherited_edges"] = inherited_edges
    _idempotency_store(
        req.workspace_id,
        f"editor:link:{req.source_id}:{req.target_id}:{req.edge_type}",
        req.idempotency_key, response,
    )
    return response


@router.post("/editor/overwrite")
def editor_overwrite(req: EditorOverwriteRequest):
    """§9.5.1 Editor.overwrite — single-field update through the lifecycle."""
    cached = _idempotency_lookup(
        req.workspace_id,
        f"editor:overwrite:{req.concept_id}:{req.field}",
        req.idempotency_key,
    )
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    # Capture pre-state for the evolution-log diff (C5 / §8D.33).
    pre_node = ge.get_concept(req.concept_id)
    pre_dict = _concept_to_dict(pre_node) if pre_node else None
    kwargs: Dict[str, Any] = {req.field: req.value}
    try:
        node = ge.update_concept(req.concept_id, **kwargs)
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"field {req.field!r}: {e}")
    # §3.1 / §12.6.1 — route through the dispatcher (WS + index + projection +
    # evolution log + cascade) instead of calling update_concept raw.
    if node is not None:
        _apply_update_lifecycle(
            node, ge, pre_dict=pre_dict, node_dict=_concept_to_dict(node),
            actor="editor",
        )
    response = {"ok": True, "concept_id": req.concept_id,
                "field": req.field,
                "updated": node is not None}
    _idempotency_store(
        req.workspace_id,
        f"editor:overwrite:{req.concept_id}:{req.field}",
        req.idempotency_key, response,
    )
    return response


@router.post("/editor/delete")
def editor_delete(req: EditorDeleteRequest):
    """§9.5.1 Editor.delete — cascade-aware tombstone via delete_concept.

    Foundation fixtures (``fixture::``) are rejected at the graph layer
    per §18.22; this endpoint surfaces that rejection as ``ok: false``
    rather than as a 5xx so the agent emit-path can swallow it.
    """
    if not req.concept_id:
        raise HTTPException(status_code=400, detail="concept_id required")
    cached = _idempotency_lookup(
        req.workspace_id, f"editor:delete:{req.concept_id}", req.idempotency_key,
    )
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    # Capture pre-delete state so the evolution log retains a rollback
    # payload (C5 / §8D.33), mirroring DELETE /concepts/{id}.
    pre_node = ge.get_concept(req.concept_id)
    pre_dict = _concept_to_dict(pre_node) if pre_node else None
    ok = ge.delete_concept(req.concept_id)
    # §3.1 — fire the delete fan-out only when the delete actually happened
    # (fixtures return ok=False at the graph layer and must NOT broadcast).
    if ok:
        _apply_delete_lifecycle(req.concept_id, pre_dict, ge, actor="editor")
    response = {"ok": bool(ok), "concept_id": req.concept_id}
    _idempotency_store(
        req.workspace_id, f"editor:delete:{req.concept_id}",
        req.idempotency_key, response,
    )
    return response


@router.post("/agent/spawn")
def agent_spawn(req: AgentSpawnRequest):
    """§8D.27 — spawn a visible agent body subgraph.

    Creates (or reuses) four concept nodes:

      1. ``parameter_card``  — the agent's state (goal, step_index,
         zone_of_influence). Skipped if ``parameter_card_id`` already
         resolves to a record.
      2. ``perception_card`` — reads the param card + apparitions.
      3. ``transformer_card``— invokes the SLM with the prompt template
         stored in its own data block.
      4. ``emitter_card``    — applies action JSON via the shared
         ActionResolver, gated by an ``allow`` filter in its data block.

    Wires them ``param → perception → transformer → emitter`` so the
    next ``/api/agent/tick`` call walks the visible chain.
    """
    cached = _idempotency_lookup(
        req.workspace_id, f"spawn:{req.parameter_card_id or req.name or '_new'}",
        req.idempotency_key,
    )
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    pcid = req.parameter_card_id or ""
    workspace_id = req.workspace_id or ""

    # Create the parameter card if it doesn't exist yet.
    existing_param = ge.get_concept(pcid) if pcid else None
    if existing_param is None:
        import json as _json
        # ``cascade_enabled`` defaults to False — the agent ticks only
        # on explicit user button-press until the user flips Auto-tick
        # on. Combined with ``paused``, this gates the §8D.38.1 loop
        # so a newly-spawned agent never starts unsupervised.
        params_data = _json.dumps({
            "goal": req.goal or "Inspect the graph and suggest one useful next concept.",
            "step_index": 0,
            "zone_of_influence": {},
            "cascade_enabled": False,
            "paused": False,
        }, indent=2)
        param_node = ge.create_concept(
            name=req.name or "agent_parameters",
            description=(
                "Agent parameter card (§8D.27): holds goal, step_index, "
                "zone_of_influence. Edit ``data`` to change the agent's "
                "goal mid-run; deletion terminates the agent."
            ),
            data=params_data,
            provenance="user-authored",
            workspace_id=workspace_id,
            type_hint="agent_parameter",
        )
        if param_node is None:
            raise HTTPException(status_code=500, detail="failed to create parameter card")
        _apply_create_lifecycle(param_node, ge)
        pcid = param_node.concept_id

    # Spawn the visible body subgraph (idempotent on re-call).
    from backend.services.agent_runtime import spawn_agent_body_subgraph
    response = spawn_agent_body_subgraph(
        graph_editor=ge,
        parameter_card_id=pcid,
        workspace_id=workspace_id,
        push_fn=_ws_push,
    )
    _idempotency_store(
        req.workspace_id, f"spawn:{req.parameter_card_id or req.name or '_new'}",
        req.idempotency_key, response,
    )
    return response


@router.get("/agent/tokens/{parameter_card_id}")
def agent_token_buffer(parameter_card_id: str, limit: int = 4000):
    """§8D.8 — retroactive fetch of the agent_token stream buffer.

    A tab that subscribes to the workspace WS after a tick has started
    misses the early tokens. This endpoint returns the last ``limit``
    tokens recorded for the parameter card so the user sees the full
    reasoning trace once their UI catches up. The buffer is in-memory
    only; ticks completed before the process started are not recovered.

    Returns ``{ parameter_card_id, count, joined, tokens: [{ts, token, workspace_id}, ...] }``.
    The ``joined`` field is the convenient concatenated string for
    panels that just want the text; ``tokens`` carries per-token
    timestamps for replay-style rendering.
    """
    try:
        from backend.services.agent_runtime import get_agent_token_buffer
        entries = get_agent_token_buffer(parameter_card_id, limit=int(limit))
        return {
            "parameter_card_id": parameter_card_id,
            "count": len(entries),
            "joined": "".join(e.get("token", "") for e in entries),
            "tokens": entries,
        }
    except Exception as e:
        return {
            "parameter_card_id": parameter_card_id,
            "count": 0, "joined": "", "tokens": [],
            "error": str(e),
        }


@router.get("/agent/cascade_status")
def agent_cascade_status(parameter_card_id: str = ""):
    """Diagnostic snapshot of the cascade scheduler (§8D.38.1).

    Returns per-agent state: total fires, age of the last fire, fires
    in the rolling 60-second window, whether a debounce timer is
    currently armed, and the reason the last schedule attempt was
    skipped (if any). The agents panel polls this to render fire
    counts and confirm AUTO mode is genuinely advancing the agent.
    """
    try:
        from backend.services.agent_runtime import get_cascade_scheduler
        return {"status": "ok", "agents": get_cascade_scheduler().status(parameter_card_id or "")}
    except Exception as e:
        return {"status": "error", "detail": str(e), "agents": {}}


@router.post("/agent/tick")
async def agent_tick(req: AgentTickRequest):
    """Fire one meta-cognition tick (§8D.27 / §8D.38).

    Reads the parameter card's data block as agent parameters,
    composes a perception payload, calls the on-device SLM with live
    token streaming, parses the SLM's JSON response into a
    MetaCognitionAction, applies the action to the canvas via the
    graph_editor, and returns a summary.

    Live tokens are emitted on the WS as ``agent_token`` frames
    while the SLM is generating.
    """
    try:
        from backend.services.agent_runtime import MetaCognitionTick
        ge = _get_graph_editor()
        app_svc = _get_apparition_service()
        ci = app_svc._concept_index  # share the same ConceptIndex singleton
        # Lazy slm client; if unavailable, the tick emits a stub action.
        slm = None
        try:
            from backend.services.slm_client import SLMClient
            slm = SLMClient()
        except Exception:
            slm = None
        tick = MetaCognitionTick(
            graph_editor=ge,
            concept_index=ci,
            apparition_service=app_svc,
            slm_client=slm,
            broadcast=_ws_push,
            workspace_id=req.workspace_id or "",
            parameter_card_id=req.parameter_card_id or "",
        )
        result = await tick.run_async()
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/concept_edges")
def create_concept_edge(req: ConceptEdgeRequest):
    # Idempotency dedup: the cache key encodes source+target so a
    # retry of the same logical edge doesn't double-broadcast.
    idem_target = f"{req.source_id}->{req.target_id}"
    cached = _idempotency_lookup(req.workspace_id, idem_target, req.idempotency_key)
    if cached is not None:
        return cached
    ge = _get_graph_editor()
    # Phase 7 EXPLORE-03 (T-07-06) — same invalid-pair validation as
    # editor_link; create_concept_edge itself never raises for an unknown
    # concept_id, so the 400 must be enforced here, preserved even when
    # inherit_types is requested (never a fast-path bypass).
    if ge.get_concept(req.source_id) is None or ge.get_concept(req.target_id) is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid edge: source_id={req.source_id!r} or target_id={req.target_id!r} not found",
        )
    edge = ge.create_concept_edge(
        source_id=req.source_id,
        target_id=req.target_id,
        edge_type=req.edge_type,
        source_port=req.source_port,
        target_port=req.target_port,
        weight=req.weight,
        variable_name=req.variable_name,
        workspace_id=req.workspace_id,
    )
    from backend.services.concept_lifecycle import apply_edge_create_lifecycle
    edge_dict = apply_edge_create_lifecycle(
        edge, ge, workspace_id=req.workspace_id or "", push_fn=_ws_push,
    )
    response = edge_dict or _edge_to_dict(edge)
    # Phase 7 EXPLORE-03 / N.4 — same single synchronous I/O-type-
    # inheritance side-effect as editor_link, fanned through the same
    # lifecycle dispatcher (RESEARCH Open-Q3). Default-False path unchanged.
    if req.inherit_types:
        inherited_edges = []
        for inherited_edge in _inherit_io_types(
            ge, req.source_id, req.target_id, req.workspace_id or "",
        ):
            apply_edge_create_lifecycle(
                inherited_edge, ge, workspace_id=req.workspace_id or "", push_fn=_ws_push,
            )
            inherited_edges.append(_edge_to_dict(inherited_edge))
        if isinstance(response, dict):
            response["inherited_edges"] = inherited_edges
    _idempotency_store(req.workspace_id, idem_target, req.idempotency_key, response)
    return response


@router.delete("/concept_edges/{edge_id}")
def delete_concept_edge_by_id(edge_id: str):
    ge = _get_graph_editor()
    # Capture the pre-delete edge so we know its workspace; without
    # this, the projection recompute would only ever fire for the
    # default workspace, regardless of where the edge lived.
    pre_edge = ge.get_concept_edge(edge_id)
    workspace_id = (pre_edge.workspace_id if pre_edge else "") or ""
    ok = ge.delete_concept_edge(edge_id)
    from backend.services.concept_lifecycle import apply_edge_delete_lifecycle
    apply_edge_delete_lifecycle(edge_id, workspace_id, ge, push_fn=_ws_push)
    return {"ok": bool(ok), "edge_id": edge_id}
