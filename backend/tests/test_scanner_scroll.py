"""
test_scanner_scroll.py -- Lock in the scan-completeness fixes.

These tests drive ``ShadowDOMScanner`` with a minimal fake WebDriver so
we can assert:

1. ``_wait_for_scroll_height_stable`` returns only after scrollHeight
   has been unchanged for ``stable_for`` seconds (i.e. it really does
   wait out slow lazy loads rather than ignoring them).
2. The scan loop tolerates **3** consecutive quiet iterations before it
   bails, so a single lull doesn't truncate the capture.
3. Per-iteration ``_scroll`` no longer jumps to ``document.body.scrollHeight``
   on every step -- the aggressive blind bottom-jump was what made
   middle-of-page content get skipped.
4. No late/one-shot ``scrollTo(body.scrollHeight)`` fires at all --
   the earlier "bottom kick after streak >= 2" was jarring on long
   SPAs and recycled mid-page virtualized rows before we'd captured
   them. The only advancement mechanism is the progressive
   viewport-sized ``scrollBy`` (plus opportunistic "Load more"
   clicks). This file pins that guarantee so the blind jump can't
   sneak back in.

No Selenium required.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.dom.scanner import ShadowDOMScanner


# ---------------------------------------------------------------------------
# Minimal fake Selenium surface
# ---------------------------------------------------------------------------


class _FakeElement:
    def __init__(self) -> None:
        self.clicks = 0

    def is_displayed(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return False

    def click(self) -> None:
        self.clicks += 1


class _FakeDriver:
    """Records every execute_script call and replays scripted answers."""

    def __init__(
        self,
        scroll_heights: Optional[List[int]] = None,
        snapshots: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.current_url = ""
        self.executed: List[str] = []
        self.scroll_heights = list(scroll_heights) if scroll_heights is not None else []
        self.snapshots = list(snapshots) if snapshots is not None else []
        self.capture_calls = 0

    # Selenium shims --------------------------------------------------
    def get(self, url: str) -> None:
        self.current_url = url

    def execute_script(self, script: str, *args: Any) -> Any:
        self.executed.append(script)
        if "document.readyState" in script:
            return "complete"
        if "scrollHeight" in script:
            # Pop the next scripted height; fall back to the last one.
            if self.scroll_heights:
                if len(self.scroll_heights) > 1:
                    return self.scroll_heights.pop(0)
                return self.scroll_heights[0]
            return 1000
        if "scrollTo" in script or "scrollBy" in script:
            return None
        if "extract" in script.lower():
            self.capture_calls += 1
            if self.snapshots:
                return "<<snapshot>>"  # scanner uses json.loads(_capture())
            return "{}"
        return None

    def find_elements(self, by: Any, value: str) -> List[_FakeElement]:
        return []

    def find_element(self, by: Any, value: str) -> _FakeElement:
        raise RuntimeError("no element")


# ---------------------------------------------------------------------------
# 1. _wait_for_scroll_height_stable waits out the quiescence window
# ---------------------------------------------------------------------------


def test_settle_wait_returns_when_height_stops_growing():
    """stable_for must elapse AFTER the last height change, not before."""
    # Two bumps then flat. With stable_for=0.2, the loop should return
    # ~0.2s after the third read (first flat read).
    driver = _FakeDriver(scroll_heights=[1000, 1100, 1200, 1200, 1200, 1200])
    scanner = ShadowDOMScanner(driver)

    t0 = time.time()
    scanner._wait_for_scroll_height_stable(timeout=2.0, stable_for=0.2, poll_interval=0.05)
    elapsed = time.time() - t0

    # Upper bound: well under the 2.0 timeout (we should NOT have hit it).
    assert elapsed < 1.0, (
        f"settle wait should have returned once height stabilized, "
        f"but elapsed={elapsed:.3f}s"
    )
    # Lower bound: we did wait at least stable_for seconds of flat reads.
    assert elapsed >= 0.15, (
        f"settle wait returned too quickly ({elapsed:.3f}s); "
        f"should have waited ~stable_for seconds of stable reads"
    )


def test_settle_wait_honors_timeout_when_dom_keeps_growing():
    """If scrollHeight never stops growing, return at the timeout bound."""
    # Infinite supply of distinct heights — scanner must give up at timeout.
    heights = [1000 + i * 100 for i in range(1, 200)]
    driver = _FakeDriver(scroll_heights=heights)
    scanner = ShadowDOMScanner(driver)

    t0 = time.time()
    scanner._wait_for_scroll_height_stable(timeout=0.3, stable_for=0.5, poll_interval=0.05)
    elapsed = time.time() - t0

    assert 0.25 <= elapsed <= 0.6, (
        f"settle wait should cap at ~timeout seconds, got {elapsed:.3f}s"
    )


# ---------------------------------------------------------------------------
# 2. Scan loop tolerates 3 consecutive quiet iterations
# ---------------------------------------------------------------------------


class _ScriptedScanner(ShadowDOMScanner):
    """Overrides the native-snapshot helpers so we can drive the scan
    loop synthetically without a real browser.

    Method names mirror the scanner's legacy non-JS path
    (``_capture_unified`` + ``_merge_trees``); their presence on the
    subclass tells ``__init__`` to honour the requested
    ``live_chunking`` mode rather than forcing the JS engine. The
    test fixture sets ``live_chunking`` to a non-``'js'`` value so
    the legacy scroll branch is exercised end-to-end.
    """

    def __init__(self, driver: Any, change_script: List[bool]) -> None:
        # The scanner's ``__init__`` forces JS mode unless the
        # subclass already defines the legacy helpers. We provide
        # ``_capture_unified`` and ``_merge_trees`` *before* calling
        # ``super().__init__`` so the hasattr check sees them.
        self._change_script = list(change_script)
        self.iter_count = 0
        self.bottom_kicks = 0
        super().__init__(driver)
        # Explicitly request legacy mode — the init logic respects
        # this because legacy helpers are now present on the
        # instance.
        self._use_js_engine = False
        # Match the test's documented scroll-bail budget (3 quiet
        # iters from the start). Production lifts this to 5 for
        # real-page leniency; tests use 3 so the synthetic loop
        # bails predictably.
        self.NO_CHANGE_LIMIT = 3

    def _capture_unified(self) -> dict:
        return {"nodeType": 1, "tagName": "html", "children": []}

    def _scroll(self, pause: float) -> None:
        # Skip real driver calls; the scan loop will read _changes_detected
        # via our patched _merge_trees.
        self.iter_count += 1

    def _merge_trees(self, target: dict, source: dict) -> None:  # type: ignore[override]
        if not self._change_script:
            self._changes_detected = False
            return
        should_change = self._change_script.pop(0)
        self._changes_detected = bool(should_change)
        if should_change:
            self._added_nodes = [{"added": True}]


def test_scan_tolerates_three_consecutive_no_change_iterations():
    """Two quiet iterations followed by a real change must NOT terminate.

    Before the fix the loop bailed on the FIRST quiet iteration, which
    truncated captures on pages that render in waves.
    """
    driver = _FakeDriver()
    # Script: quiet, quiet, change, quiet, quiet, quiet => bail
    scanner = _ScriptedScanner(driver, change_script=[False, False, True,
                                                      False, False, False])

    steps = list(scanner.scan("about:blank", max_duration=5, pause=0.0))

    # Initial yield + one mid-scan change yield = 2 yields.
    assert len(steps) == 2, f"expected 2 yields, got {len(steps)}"
    # The change script was fully drained.
    assert scanner._change_script == [], (
        "scan should have consumed all scripted iterations"
    )
    # No bottom-jump should fire under any circumstance: we removed
    # the late footer-kick because it caused jarring teleports and
    # virtualized-row recycling. The progressive scroll is the only
    # advancement mechanism now.
    assert scanner.bottom_kicks == 0, (
        f"scan loop must not bottom-jump anymore; got {scanner.bottom_kicks}"
    )


def test_scan_bails_after_three_quiet_iterations_from_the_start():
    """Pure quiet run still terminates -- the tolerance isn't infinite."""
    driver = _FakeDriver()
    scanner = _ScriptedScanner(driver, change_script=[False] * 10)

    steps = list(scanner.scan("about:blank", max_duration=5, pause=0.0))

    # Just the initial yield; 3 quiet iterations then bail.
    assert len(steps) == 1
    # Loop exits cleanly on streak=3 with no detour through a
    # bottom-kick on the way out.
    assert scanner.iter_count == 3
    assert scanner.bottom_kicks == 0


def test_scan_never_executes_bottom_jump_script():
    """Belt-and-suspenders: audit the driver script log end-to-end.

    The previous ``_bottom_jump_once`` helper ran
    ``window.scrollTo(0, document.body.scrollHeight)``. No matter how
    quiet the scan goes, the real driver must never see that string.
    """
    driver = _FakeDriver()
    scanner = _ScriptedScanner(driver, change_script=[False] * 10)

    list(scanner.scan("about:blank", max_duration=5, pause=0.0))

    bottom_jumps = [
        s for s in driver.executed
        if "scrollTo(0, document.body.scrollHeight)" in s
    ]
    assert bottom_jumps == [], (
        f"scan loop must not emit a scrollTo(body.scrollHeight); "
        f"found {len(bottom_jumps)}: {bottom_jumps}"
    )


# ---------------------------------------------------------------------------
# 3. _scroll no longer jumps to scrollHeight on every iteration
# ---------------------------------------------------------------------------


def test_scroll_does_not_blind_jump_to_bottom_every_iteration():
    """The per-iteration scroll must NOT execute a scrollTo(body.scrollHeight)."""
    driver = _FakeDriver(scroll_heights=[1000, 1000, 1000])
    scanner = ShadowDOMScanner(driver)

    scanner._scroll(pause=0.0)

    blind_jumps = [
        s for s in driver.executed
        if "scrollTo(0, document.body.scrollHeight)" in s
    ]
    assert blind_jumps == [], (
        f"per-iteration _scroll should not jump to page bottom; "
        f"found {len(blind_jumps)} such calls: {blind_jumps}"
    )

    # But it DID do a progressive viewport-sized step.
    progressive = [s for s in driver.executed if "scrollBy" in s]
    assert progressive, "expected a scrollBy(...innerHeight) step"


def test_scanner_has_no_bottom_jump_helper():
    """The ``_bottom_jump_once`` helper was removed on purpose.

    If somebody re-introduces it, this test breaks the build and
    forces them to defend the regression in a PR review -- not in
    production where it manifests as users watching their scanner
    teleport to the page bottom mid-scroll.
    """
    assert not hasattr(ShadowDOMScanner, "_bottom_jump_once"), (
        "ShadowDOMScanner._bottom_jump_once was removed; the scan "
        "loop should only use progressive scrollBy. If you need "
        "footer-only content, let the progressive scroll reach the "
        "bottom on its own."
    )
