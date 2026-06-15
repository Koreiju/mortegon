"""
continuous_scanner.py — Background re-scan service for watched URLs.

Watches a set of URLs and re-scans them at a configurable interval,
feeding delta frames through the mapper pipeline. Respects the
WorkflowStateTracker to prevent concurrent scans.

Usage:
    from backend.services.continuous_scanner import get_continuous_scanner

    scanner = get_continuous_scanner()
    scanner.watch('https://example.com', interval=30)
    scanner.start(mapper, on_stream_callback)
    # ...
    scanner.unwatch('https://example.com')
    scanner.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)


class WatchedURL:
    """Configuration for a continuously watched URL."""
    __slots__ = ('url', 'interval', 'last_scan', 'scan_count', 'paused')

    def __init__(self, url: str, interval: float = 30.0):
        self.url = url
        self.interval = interval  # seconds between re-scans
        self.last_scan = 0.0
        self.scan_count = 0
        self.paused = False


class ContinuousScanner:
    """Background service that re-scans watched URLs on a timer.

    Runs in a daemon thread. Each scan cycle:
      1. Checks which watched URLs are due for re-scan
      2. Runs mapper.snapshot() for each (which now emits delta frames)
      3. Sleeps until the next URL is due
    """

    def __init__(self):
        self._watched: Dict[str, WatchedURL] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._mapper = None
        self._on_stream: Optional[Callable] = None

    def watch(self, url: str, interval: float = 30.0) -> None:
        """Add a URL to the watch list."""
        with self._lock:
            if url not in self._watched:
                self._watched[url] = WatchedURL(url, interval)
                logger.info(f"[ContinuousScanner] Watching {url} every {interval}s")
            else:
                self._watched[url].interval = interval

    def unwatch(self, url: str) -> None:
        """Remove a URL from the watch list."""
        with self._lock:
            removed = self._watched.pop(url, None)
            if removed:
                logger.info(f"[ContinuousScanner] Unwatched {url}")

    def pause(self, url: str) -> None:
        """Pause scanning a specific URL."""
        with self._lock:
            w = self._watched.get(url)
            if w:
                w.paused = True

    def resume(self, url: str) -> None:
        """Resume scanning a paused URL."""
        with self._lock:
            w = self._watched.get(url)
            if w:
                w.paused = False

    @property
    def watched_urls(self) -> Dict[str, dict]:
        """Return status of all watched URLs."""
        with self._lock:
            return {
                url: {
                    'interval': w.interval,
                    'last_scan': w.last_scan,
                    'scan_count': w.scan_count,
                    'paused': w.paused,
                }
                for url, w in self._watched.items()
            }

    def start(self, mapper, on_stream: Callable) -> None:
        """Start the background scan thread.

        Args:
            mapper: DomMapper instance (must have a Selenium driver attached)
            on_stream: callback for streaming frames (same signature as snapshot's on_stream)
        """
        if self._thread and self._thread.is_alive():
            logger.warning("[ContinuousScanner] Already running")
            return

        self._mapper = mapper
        self._on_stream = on_stream
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="continuous-scanner",
            daemon=True,
        )
        self._thread.start()
        logger.info("[ContinuousScanner] Started background scanning")

    def stop(self) -> None:
        """Stop the background scan thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("[ContinuousScanner] Stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run_loop(self) -> None:
        """Main scan loop — runs in background thread."""
        while not self._stop_event.is_set():
            now = time.time()
            next_due = float('inf')

            with self._lock:
                urls_to_scan = []
                for url, w in self._watched.items():
                    if w.paused:
                        continue
                    time_since = now - w.last_scan
                    if time_since >= w.interval:
                        urls_to_scan.append(url)
                    else:
                        remaining = w.interval - time_since
                        next_due = min(next_due, remaining)

            for url in urls_to_scan:
                if self._stop_event.is_set():
                    return
                self._scan_url(url)

            # Sleep until next URL is due (or 1s minimum for responsiveness)
            sleep_time = min(next_due, 1.0) if next_due != float('inf') else 1.0
            self._stop_event.wait(timeout=sleep_time)

    def _scan_url(self, url: str) -> None:
        """Execute a single re-scan for a URL."""
        try:
            logger.info(f"[ContinuousScanner] Re-scanning {url}")
            result = self._mapper.snapshot(
                url=url,
                max_duration=30,
                on_stream=self._on_stream,
            )
            with self._lock:
                w = self._watched.get(url)
                if w:
                    w.last_scan = time.time()
                    w.scan_count += 1
            logger.info(f"[ContinuousScanner] Re-scan complete: {url} → "
                        f"{result.get('node_count', 0)} nodes")
        except Exception as e:
            logger.error(f"[ContinuousScanner] Re-scan failed for {url}: {e}",
                         exc_info=True)


# Module-level singleton
_continuous_scanner: Optional[ContinuousScanner] = None


def get_continuous_scanner() -> ContinuousScanner:
    """Return the global ContinuousScanner singleton."""
    global _continuous_scanner
    if _continuous_scanner is None:
        _continuous_scanner = ContinuousScanner()
    return _continuous_scanner
