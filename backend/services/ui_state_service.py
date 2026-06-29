"""ui_state_service.py — Per-workspace UI state mirror.

The frontend's 3D / 2D surfaces carry transient UI state that the
backend used to be oblivious to: which chunk is currently
*selected* (the 3D scene's focal target), which is *hovered* (for
apparition-halo previews), which billboard panels are currently
*pinned* (the click-and-stick set per §8D.1).

Historically these lived only inside the browser tab — making it
impossible for the CLI harness, an agent, or peer tabs to know
what the human user is attending to. This service is the
server-side mirror: REST endpoints write to it, every mutation
broadcasts a ``ui_state_changed`` WS frame, peer tabs reconcile
their local UI state from the broadcast.

Read paths:
  - ``Database.selected_id`` (§8D.12 fixture property) resolves
    here via its backing pointer.
  - The apparition triple-product (§8D.43) can weight candidates
    by recency-of-pin to surface "what the user just touched".
  - The CLI harness's ``ui-state`` action returns the snapshot.

Write paths:
  - ``POST /api/ui/select``, ``/pin``, ``/unpin``, ``/hover``.
  - Future: WS-side ``ui_select`` / ``ui_pin`` frames from the
    frontend mirror these same setters.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class UIState:
    """One workspace's UI snapshot.

    Fields are intentionally minimal — keep them mirroring real
    frontend state, don't bloat with backend-only tracking.
    """
    selected_id: Optional[str] = None
    hovered_id:  Optional[str] = None
    # Ordered set: insertion order matches click sequence so peer
    # tabs can replay the user's recent attention focus.
    pinned_billboards: List[str] = field(default_factory=list)
    # §UnifiedNodeView — per-pinned-node collapsed flag. Default
    # sticky behavior per Mortegon Integration Scheme §1: a freshly
    # pinned panel materialises **collapsed**; the user uncollapses
    # it explicitly. Passive (not hovered, not clicked) panels stay
    # collapsed. Key = node_id (must also appear in pinned_billboards).
    pinned_collapsed: Dict[str, bool] = field(default_factory=dict)
    # The screen-rect (top-left + width/height) the hover panel was
    # showing at the moment the click landed. Used to enforce the
    # "stick at hover position" parity contract: the pinned panel
    # spawns at exactly this rect, not a fixed location. Set by the
    # frontend on the click event AND mirrored here so the REPL can
    # assert the parity contract was honoured.
    last_hover_rect: Optional[Dict[str, float]] = None
    last_stick_rect: Optional[Dict[str, float]] = None
    # Per-URL collapse flag — when True, the chunks of that URL AND
    # any pinned billboards/3D nodes referencing those chunks must
    # hide. Animate loop reads this flag; the REPL queries it via
    # /api/ui/state and /api/ui/url_visibility.
    url_collapsed: Dict[str, bool] = field(default_factory=dict)
    # Per-pinned-billboard-id → url-it-was-spawned-from. Lets the
    # backend resolve which billboards a URL-collapse should hide.
    billboard_url: Dict[str, str] = field(default_factory=dict)
    # §8D.2.2 — right-click compile/collapse mirror. Maps the central
    # concept_id of a panel currently expanded into a simplified
    # subgraph to the metadata that lets peer surfaces (REPL, peer
    # tabs, agent perception) read which expansions are in flight and
    # which child ids belong to each. Empty when no panel is expanded.
    #   { central_concept_id: { "children": [child_id, ...],
    #                            "expanded_at": <float epoch> } }
    compile_expansions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # §8.2 / §14.2 — apparition halo focus mirror. When the user (or
    # the agent) opens an apparition halo on a focal panel, the
    # frontend POSTs the focal id + the ranked candidate list here.
    # Peer surfaces (REPL viewer, agent perception, peer tabs) read
    # this to know which card is currently radiating, what candidates
    # the user is seeing, and the triple-product breakdown of each.
    # Cleared on halo close (mouseleave + debounce).
    #   { "focal_card_id": <id>,
    #     "candidates":    [{card_id, score, pagerank, tfidf_cos,
    #                        nomic_cos, name?}, ...],
    #     "opened_at":     <float epoch> }
    # None when no halo is open.
    halo_focus: Optional[Dict[str, Any]] = None
    # §17.12 / §14.2 — per-panel chrome (drag/resize/minimise state).
    # Keyed by panel_id (the node_id of the pinned billboard). Each
    # record carries {top, left, width, height, minimised}. The pin()
    # setter initialises with sensible defaults on first pin; per-field
    # setters merge over the existing record so drag (top/left only),
    # resize (width/height only), and minimise (minimised only) compose.
    # Cleared on unpin().
    pin_chrome: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # §17.13 / §4.4 — per-card latch state. Values are "latched" |
    # "unlatched". Missing key = treated as "latched" (default). The
    # toggle setter flips; explicit set is idempotent.
    latch_state: Dict[str, str] = field(default_factory=dict)
    # §17.14 / §6.4 / §8.3 — IntersectionObserver-driven viewport
    # spine mirror. The frontend POSTs the *ordered* list of chunk_ids
    # currently in the scroll viewport plus the total row count; the
    # 3D animate loop reads this to apply chunkCollapseTarget=0 to
    # visible chunks only, and the agent's zone_of_influence reads it
    # to know what the user is attending to. None when no retrieval
    # list is active.
    #   {"ordered": [chunk_id, ...], "total": N, "updated_at": <epoch>}
    viewport_visible_rows: Optional[Dict[str, Any]] = None
    # §17.15 / §4.7 — active autocomplete dropdown mirror. When the
    # user types into an editable row's name field, the frontend POSTs
    # the {row_id, query, parent_card_id?} here so peer surfaces see
    # the active autocomplete state and so the candidate list (fetched
    # separately via /api/concept_completions) can be associated with
    # the open dropdown. Cleared on dropdown dismiss / select.
    #   {"row_id": <id>, "query": <text>, "parent_card_id": <id> | None,
    #    "candidates": [{card_id, name, score, ...}, ...],
    #    "opened_at": <epoch>}
    autocomplete_state: Optional[Dict[str, Any]] = None
    # §4.1.1 / §1.1 Imaginary — click-to-edit-then-Enter transient state.
    # When a user clicks a print-rendered token to open it for editing,
    # the frontend POSTs {card_id, field_path, value_so_far} here so peer
    # surfaces see what is being edited in real time. Cleared on Enter /
    # Escape / blur (the field returns to print form).
    #   {"card_id": <id>, "field_path": "<key>" | "<key>.<subkey>",
    #    "value_so_far": <text>, "opened_at": <epoch>}
    editing_field: Optional[Dict[str, Any]] = None
    # §8.2.2 / §1.1 Imaginary — autoregressive halo chain. As the user
    # walks the retrieval space by clicking halo phantoms (each click
    # spawning a new focal whose own halo radiates), this list records
    # the ordered focal_card_ids visited since the chain opened. Empty
    # list = no chain in progress. Reset on explicit dismiss or
    # purge_workspace.
    halo_chain: List[str] = field(default_factory=list)
    # §4.6.1 signal-stream constraint — one signal at a time under
    # iteration. Each entry keys by the iterable card_id and carries
    # ``{card_id, total, signal_index, signal_id?, field_path, paused,
    # updated_at, ordered?}``. The RolloutCoordinator advances
    # ``signal_index`` per play step; the panel renderer reads this to show
    # ONLY the active signal (anti-goal §18.24 — full-iterable rendering
    # would violate it).
    # STEP-01 / D10 — when ``ordered`` (the card's ordered sampled-chunk
    # concept_id list) is registered, ``signal_id`` is resolved SERVER-SIDE
    # as ``ordered[signal_index]`` on every set/advance — a real 3D chunk id
    # the frontend stepper (`fe/stepper.mjs`) reads to drive
    # `projector.flyToNode`/`highlightNode`. The frontend never indexes into
    # a client-side array itself (data correlation stays backend-side).
    signal_stream: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # §7.5 / RolloutCoordinator.md §2.4 — the active iterated rollout summary
    # ``{card_id, field_path, paused, signal_index, signal_total, node_id} | None``.
    # The RolloutCoordinator (play/pause/step/reset) owns this; the frontend
    # play/pause control + the REPL viewer read it.
    rollout_state: Optional[Dict[str, Any]] = None
    # §7.3.4 / object_exploration — inline node-fold state. Right-clicking a
    # ``{ref}`` token in a card's field-tree toggles that token's path open
    # (rank-1 inline reveal of the referenced node) without leaving the panel.
    # ``{card_id: {"expanded_paths": [<field_path>, ...], "updated_at": <epoch>}}``.
    node_fold_state: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # §6.6.5 / §7.3.5 — generalized rank-dominance collapse (Q.3–Q.5).
    # Right-clicking a *dominator* node (a root-URL doc-hub in 3D, or a
    # bisector compute node, or a panel/graph node in 2D) folds its
    # dominated set and — in the 3D projector — hides every other node
    # (the isolate). Keyed by the dominator's node/concept id:
    # ``{node_id: {"collapsed": bool, "hidden_set": [ids], "folded_set":
    #   [ids], "updated_at": <epoch>}}``. Membership (hidden/folded sets)
    # is the dominator's dominated-set reachability over the ConceptEdge
    # graph (DOMAIN §8.1.2) — the same graph PageRank runs over.
    dominance_collapse: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_changed_at:    float = 0.0
    last_change_kind:   str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_id":       self.selected_id,
            "hovered_id":        self.hovered_id,
            "pinned_billboards": list(self.pinned_billboards),
            "pinned_collapsed":  dict(self.pinned_collapsed),
            "last_hover_rect":   self.last_hover_rect,
            "last_stick_rect":   self.last_stick_rect,
            "url_collapsed":     dict(self.url_collapsed),
            "billboard_url":     dict(self.billboard_url),
            "compile_expansions": {
                k: dict(v) for k, v in self.compile_expansions.items()
            },
            "halo_focus":        (dict(self.halo_focus)
                                  if self.halo_focus else None),
            "pin_chrome":        {k: dict(v) for k, v in self.pin_chrome.items()},
            "latch_state":       dict(self.latch_state),
            "viewport_visible_rows": (dict(self.viewport_visible_rows)
                                      if self.viewport_visible_rows else None),
            "autocomplete_state": (dict(self.autocomplete_state)
                                   if self.autocomplete_state else None),
            "editing_field":     (dict(self.editing_field)
                                  if self.editing_field else None),
            "halo_chain":        list(self.halo_chain),
            "signal_stream":     {k: dict(v) for k, v in self.signal_stream.items()},
            "rollout_state":     (dict(self.rollout_state)
                                  if self.rollout_state else None),
            "node_fold_state":   {k: dict(v) for k, v in self.node_fold_state.items()},
            "dominance_collapse": {k: dict(v) for k, v in self.dominance_collapse.items()},
            "last_changed_at":   self.last_changed_at,
            "last_change_kind":  self.last_change_kind,
        }


class UIStateService:
    """Thread-safe per-workspace UI state mirror.

    Singleton accessed via :func:`get_ui_state_service`. Every setter
    invokes ``broadcast(0, frame)`` if a broadcast callable was wired
    at construction so peer tabs / the CLI's WS drain see the change.
    """

    def __init__(
        self,
        *,
        broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    ) -> None:
        self._states: Dict[str, UIState] = {}
        self._lock = threading.Lock()
        self._broadcast = broadcast

    # -- mutation --------------------------------------------------------
    def _stamp(
        self, st: "UIState", workspace_id: str, change_kind: str,
    ) -> "UIState":
        """Record the change marker + return the canonical snapshot, both
        under the caller's already-held ``self._lock``.

        Centralises the invariant — *every mutator stamps
        ``last_changed_at`` + ``last_change_kind`` then snapshots under the
        lock* — that was previously copy-pasted across ~26 call sites. A
        new mutator that forgot the triple would silently break the
        mirror's change-tracking (and the REPL ``watch-activity`` row that
        reads ``last_change_kind``); keeping it in one place makes the
        invariant structural rather than convention.

        KISS over a context manager: the lock + ``setdefault`` + ``_emit``
        stay visible in each mutator; only the uniform stamp+snapshot
        triple is factored out, so conditional / computed-kind variants
        (``set_collapsed``, ``set_url_collapsed``) compose by simply
        calling this inside their own branch (or not at all).

        MUST be called while holding ``self._lock``.
        """
        st.last_changed_at = time.time()
        st.last_change_kind = change_kind
        return self._snapshot_locked(workspace_id)

    def select(self, workspace_id: str, node_id: Optional[str]) -> UIState:
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.selected_id = node_id
            snap = self._stamp(st, workspace_id, "select")
        self._emit("select", workspace_id, snap)
        return snap

    def hover(self, workspace_id: str, node_id: Optional[str]) -> UIState:
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.hovered_id = node_id
            snap = self._stamp(st, workspace_id, "hover")
        self._emit("hover", workspace_id, snap)
        return snap

    def set_url_collapsed(
        self, workspace_id: str, url: str, collapsed: bool,
    ) -> UIState:
        """Collapse / expand a URL's chunk cluster. When collapsed,
        the frontend's animate loop hides the chunk spheres AND any
        pinned billboards whose source URL matches (the cascade the
        user flagged in Mortegon §5).

        Returns the snapshot AND emits a ``ui_url_visibility_changed``
        WS frame so peer tabs + the REPL drain see it.
        """
        if not url:
            raise ValueError("set_url_collapsed requires a non-empty url")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.url_collapsed[url] = bool(collapsed)
            # Identify which pinned billboards belong to this URL — the
            # frontend uses this to drop scale=0 on them next frame.
            affected = [
                bid for bid, u in st.billboard_url.items() if u == url
            ]
            snap = self._stamp(
                st, workspace_id,
                "url_collapse" if collapsed else "url_expand",
            )
        # Custom emit carrying the affected-billboard list — that's what
        # makes the cascade testable via the REPL ws drain (the standard
        # ui_state_changed snapshot doesn't enumerate the affected set).
        if self._broadcast is not None:
            try:
                self._broadcast(0, {
                    "type":             "ui_url_visibility_changed",
                    "workspace_id":     workspace_id or "_default",
                    "url":              url,
                    "hidden":           bool(collapsed),
                    "affected_billboards": affected,
                    "state":            snap.to_dict(),
                })
            except Exception:
                pass
        return snap

    def register_billboard_url(
        self, workspace_id: str, billboard_id: str, url: str,
    ) -> UIState:
        """Tell the mirror which URL spawned a given pinned billboard.
        The frontend calls this immediately after pinning so the
        URL-collapse cascade can resolve which billboards to hide."""
        if not billboard_id:
            raise ValueError("register_billboard_url requires a non-empty billboard_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.billboard_url[billboard_id] = url or ""
            snap = self._stamp(st, workspace_id, "register_billboard_url")
        self._emit("register_billboard_url", workspace_id, snap)
        return snap

    def get_hidden_billboards(
        self, workspace_id: str,
    ) -> List[str]:
        """Return the set of currently-pinned billboards that should be
        hidden because their source URL is collapsed. Pure-read; used by
        REPL scenarios to assert the cascade contract."""
        with self._lock:
            st = self._states.get(workspace_id) or UIState()
            return [
                bid for bid in st.pinned_billboards
                if st.url_collapsed.get(st.billboard_url.get(bid, ""), False)
            ]

    def pin(
        self, workspace_id: str, node_id: str,
        *, collapsed: bool = True,
        stick_rect: Optional[Dict[str, float]] = None,
    ) -> UIState:
        """Idempotent — re-pinning an already-pinned id is a no-op
        for the pin list, but DOES update the collapsed flag and the
        stick_rect (matching the user's most recent click position).

        ``collapsed`` defaults to True per the §UnifiedNodeView
        contract: a freshly pinned panel materialises collapsed; user
        must explicitly expand. ``stick_rect`` is the screen position
        the click landed at; the frontend reads it to materialise the
        pinned panel exactly where the hover preview was showing
        (Mortegon Integration Scheme §1.2 step 4).
        """
        if not node_id:
            raise ValueError("pin requires a non-empty node_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            if node_id not in st.pinned_billboards:
                st.pinned_billboards.append(node_id)
            st.pinned_collapsed[node_id] = bool(collapsed)
            if stick_rect is not None:
                st.last_stick_rect = dict(stick_rect)
            snap = self._stamp(st, workspace_id, "pin")
        self._emit("pin", workspace_id, snap)
        return snap

    def unpin(self, workspace_id: str, node_id: str) -> UIState:
        """Idempotent — unpinning a not-pinned id is a no-op."""
        if not node_id:
            raise ValueError("unpin requires a non-empty node_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            try:
                st.pinned_billboards.remove(node_id)
            except ValueError:
                pass
            # Drop the collapsed entry too — un-pinned id should not
            # leave dangling per-id state.
            st.pinned_collapsed.pop(node_id, None)
            # §17.12 — also drop the chrome record so a future re-pin
            # starts with defaults rather than the prior rect (the
            # user's intent on unpin is "forget this panel").
            st.pin_chrome.pop(node_id, None)
            snap = self._stamp(st, workspace_id, "unpin")
        self._emit("unpin", workspace_id, snap)
        return snap

    def set_collapsed(
        self, workspace_id: str, node_id: str, collapsed: bool,
    ) -> UIState:
        """Toggle a pinned panel's collapsed flag. No-op if not pinned."""
        if not node_id:
            raise ValueError("set_collapsed requires a non-empty node_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            if node_id in st.pinned_billboards:
                st.pinned_collapsed[node_id] = bool(collapsed)
                snap = self._stamp(
                    st, workspace_id,
                    "expand" if not collapsed else "collapse",
                )
            else:
                snap = self._snapshot_locked(workspace_id)
        self._emit(
            "expand" if not collapsed else "collapse",
            workspace_id, snap,
        )
        return snap

    def compile_expand(
        self, workspace_id: str, central_id: str,
        *, children: Optional[List[str]] = None,
    ) -> UIState:
        """§8D.2.2 — record that ``central_id``'s panel is currently
        expanded into a simplified subgraph with ``children`` as the
        per-key child concepts. Idempotent on central_id; the latest
        call wins. Children may be ``None`` if the frontend hasn't
        materialised them yet; the REPL still sees the central key.
        """
        if not central_id:
            raise ValueError("compile_expand requires a non-empty central_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.compile_expansions[central_id] = {
                "children":     list(children or []),
                "expanded_at":  time.time(),
            }
            snap = self._stamp(st, workspace_id, "compile_expand")
        self._emit("compile_expand", workspace_id, snap)
        return snap

    def compile_collapse(
        self, workspace_id: str, central_id: str,
    ) -> UIState:
        """§8D.2.2 — collapse the right-click expansion for ``central_id``,
        restoring the panel to its non-expanded form. Idempotent: collapsing
        a not-currently-expanded id is a no-op (but still emits a state
        update so peer surfaces can re-sync if they were stale).
        """
        if not central_id:
            raise ValueError("compile_collapse requires a non-empty central_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.compile_expansions.pop(central_id, None)
            snap = self._stamp(st, workspace_id, "compile_collapse")
        self._emit("compile_collapse", workspace_id, snap)
        return snap

    def set_halo_focus(
        self, workspace_id: str, focal_card_id: str,
        *, candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> UIState:
        """§8.2 / §14.2 — record the focal of the currently-open
        apparition halo and its ranked candidates. Idempotent on
        ``focal_card_id``; the latest call wins. ``candidates`` is the
        triple-product-ranked candidate list the user is seeing
        (each row carries ``{card_id, score, pagerank, tfidf_cos,
        nomic_cos, name?}``). The REPL viewer (§14.5) renders the
        focal + candidate count from this mirror.

        Pass ``candidates=None`` to record a focal-only update (the
        candidates were unchanged); pass an empty list to record an
        empty ranking (rare — usually clear_halo_focus is preferred).
        """
        if not focal_card_id:
            raise ValueError("set_halo_focus requires a non-empty focal_card_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            prior = st.halo_focus or {}
            prior_candidates = prior.get("candidates") or []
            new_candidates = (list(candidates) if candidates is not None
                              else list(prior_candidates))
            st.halo_focus = {
                "focal_card_id": focal_card_id,
                "candidates":    new_candidates,
                "opened_at":     time.time(),
            }
            snap = self._stamp(st, workspace_id, "halo_focus")
        self._emit("halo_focus", workspace_id, snap)
        return snap

    def clear_halo_focus(self, workspace_id: str) -> UIState:
        """§8.2 — close the apparition halo mirror (mouseleave +
        debounce, explicit dismiss, or focal panel close). Idempotent:
        clearing an already-clear halo still emits a state update so
        peer surfaces can re-sync if they were stale.
        """
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.halo_focus = None
            snap = self._stamp(st, workspace_id, "halo_clear")
        self._emit("halo_clear", workspace_id, snap)
        return snap

    # -- §17.12 — pin chrome (move / resize / minimise) ----------------
    def set_pin_chrome(
        self, workspace_id: str, panel_id: str,
        *,
        top: Optional[float] = None,
        left: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        minimised: Optional[bool] = None,
    ) -> UIState:
        """§17.12 — merge per-panel chrome state. Each kwarg is optional;
        only the fields explicitly passed are merged into the existing
        record. First call for a panel_id seeds with defaults
        (top=0, left=0, width=320, height=240, minimised=False).
        Idempotent: same kwargs → same state but still emits.
        """
        if not panel_id:
            raise ValueError("set_pin_chrome requires a non-empty panel_id")
        defaults = {
            "top": 0.0, "left": 0.0,
            "width": 320.0, "height": 240.0,
            "minimised": False,
        }
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            cur = dict(st.pin_chrome.get(panel_id) or defaults)
            if top is not None:       cur["top"] = float(top)
            if left is not None:      cur["left"] = float(left)
            if width is not None:     cur["width"] = float(width)
            if height is not None:    cur["height"] = float(height)
            if minimised is not None: cur["minimised"] = bool(minimised)
            st.pin_chrome[panel_id] = cur
            snap = self._stamp(st, workspace_id, "pin_chrome")
        self._emit("pin_chrome", workspace_id, snap)
        return snap

    # -- §17.13 — latch state (per-card) ------------------------------
    def set_latch(
        self, workspace_id: str, card_id: str,
        *, latched: Optional[bool] = None,
    ) -> UIState:
        """§17.13 — set the latch state of a card. ``latched=True`` →
        "latched"; ``latched=False`` → "unlatched"; ``latched=None`` →
        toggle current (missing = treated as "latched" so the toggle
        unlatches). Read-only python-native panels (§9.6) ignore the
        slide-out on the frontend, but the mirror still records the
        request so peer surfaces see the intent."""
        if not card_id:
            raise ValueError("set_latch requires a non-empty card_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            current = st.latch_state.get(card_id, "latched")
            if latched is None:
                new = "unlatched" if current == "latched" else "latched"
            else:
                new = "latched" if latched else "unlatched"
            st.latch_state[card_id] = new
            snap = self._stamp(st, workspace_id, "latch")
        self._emit("latch", workspace_id, snap)
        return snap

    # -- §17.14 — viewport spine (IntersectionObserver mirror) -------
    def set_viewport_spine(
        self, workspace_id: str,
        ordered: List[str], total: int,
    ) -> UIState:
        """§17.14 — record the ordered list of chunk_ids currently in
        the scroll viewport plus the total row count. Empty ordered +
        total=0 is the default (no retrieval list active). Pass None
        for ordered to clear (equivalent to empty)."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            if not ordered:
                st.viewport_visible_rows = None
            else:
                st.viewport_visible_rows = {
                    "ordered":    list(ordered),
                    "total":      int(total),
                    "updated_at": time.time(),
                }
            snap = self._stamp(st, workspace_id, "viewport_spine")
        self._emit("viewport_spine", workspace_id, snap)
        return snap

    # -- §17.15 — autocomplete state ---------------------------------
    def set_autocomplete(
        self, workspace_id: str,
        row_id: str, query: str,
        *,
        parent_card_id: Optional[str] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> UIState:
        """§17.15 — open or update the autocomplete dropdown mirror.
        Two-stage gesture: the first call (typing) opens the dropdown
        with the query but empty candidates; a second call after
        /api/concept_completions fetches the ranked candidates merges
        them in. Pass ``candidates=None`` to keep prior candidates;
        empty list to record explicit empty."""
        if not row_id:
            raise ValueError("set_autocomplete requires a non-empty row_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            prior = st.autocomplete_state or {}
            new_candidates = (list(candidates) if candidates is not None
                              else list(prior.get("candidates") or []))
            st.autocomplete_state = {
                "row_id":         row_id,
                "query":          query,
                "parent_card_id": parent_card_id,
                "candidates":     new_candidates,
                "opened_at":      time.time(),
            }
            snap = self._stamp(st, workspace_id, "autocomplete_open")
        self._emit("autocomplete_open", workspace_id, snap)
        return snap

    def clear_autocomplete(self, workspace_id: str) -> UIState:
        """§17.15 — dismiss the autocomplete dropdown mirror. Idempotent."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.autocomplete_state = None
            snap = self._stamp(st, workspace_id, "autocomplete_close")
        self._emit("autocomplete_close", workspace_id, snap)
        return snap

    # -- §4.1.1 — click-to-edit-then-Enter field state ---------------
    def set_editing_field(
        self, workspace_id: str, card_id: str, field_path: str,
        *, value_so_far: str = "",
    ) -> UIState:
        """§4.1.1 — record that a pure-print field has been clicked
        open for editing. ``field_path`` is the dotted path inside the
        card's field-tree (``description``, ``data.url``, etc.).
        ``value_so_far`` is the current textarea content (may be
        empty on first open). Idempotent on (card_id, field_path);
        subsequent calls update value_so_far. Cleared on Enter /
        Escape / blur via :meth:`clear_editing_field`."""
        if not card_id:
            raise ValueError("set_editing_field requires a non-empty card_id")
        if not field_path:
            raise ValueError("set_editing_field requires a non-empty field_path")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            prior = st.editing_field or {}
            st.editing_field = {
                "card_id":      card_id,
                "field_path":   field_path,
                "value_so_far": value_so_far,
                "opened_at":    prior.get("opened_at") or time.time(),
            }
            snap = self._stamp(st, workspace_id, "edit_open")
        self._emit("edit_open", workspace_id, snap)
        return snap

    def clear_editing_field(self, workspace_id: str) -> UIState:
        """§4.1.1 — commit / cancel / blur the active edit. Idempotent;
        clearing a not-currently-editing state still emits so peer
        surfaces can re-sync."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.editing_field = None
            snap = self._stamp(st, workspace_id, "edit_close")
        self._emit("edit_close", workspace_id, snap)
        return snap

    # -- §8.2.2 — autoregressive halo chain --------------------------
    def push_halo_chain(
        self, workspace_id: str, focal_card_id: str,
    ) -> UIState:
        """§8.2.2 — append a new focal to the autoregressive halo
        chain. Called when the user (or agent) clicks a halo phantom
        and a new focal materialises. Idempotent on
        consecutive-duplicate (no-op if the new focal equals the last
        one in the chain — re-emitting the same focal is a re-target,
        not an extension)."""
        if not focal_card_id:
            raise ValueError("push_halo_chain requires a non-empty focal_card_id")
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            if not st.halo_chain or st.halo_chain[-1] != focal_card_id:
                st.halo_chain.append(focal_card_id)
            snap = self._stamp(st, workspace_id, "halo_chain_push")
        self._emit("halo_chain_push", workspace_id, snap)
        return snap

    def clear_halo_chain(self, workspace_id: str) -> UIState:
        """§8.2.2 — reset the halo chain. Called on explicit dismiss
        (user navigates away) or implicitly by purge_workspace."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.halo_chain.clear()
            snap = self._stamp(st, workspace_id, "halo_chain_clear")
        self._emit("halo_chain_clear", workspace_id, snap)
        return snap

    @staticmethod
    def _resolve_signal_id(
        ordered: Optional[List[str]], signal_index: int,
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        """STEP-01 / D10 — resolve the 3D chunk id at ``signal_index`` from
        the card's ordered sampled-chunk list, server-side. Bounds the index
        against ``len(ordered)`` (V5 — a total/ordered length mismatch
        resolves to None rather than raising); when no ordered list is
        supplied, preserves ``fallback`` (the prior entry's signal_id) so
        existing callers that never pass ``ordered`` do not regress."""
        if not ordered:
            return fallback
        if 0 <= signal_index < len(ordered):
            return ordered[signal_index]
        return None

    def set_signal_stream(
        self, workspace_id: str,
        card_id: str, *,
        total: int = 0,
        signal_index: int = 0,
        signal_id: Optional[str] = None,
        paused: bool = False,
        field_path: str = "",
        ordered: Optional[List[str]] = None,
    ) -> UIState:
        """§4.6.1 signal-stream constraint — register or update the
        per-iterable card's signal-stream cursor.

        The RolloutCoordinator advances ``signal_index`` per play step;
        the panel renderer reads this to show ONLY the active signal.
        Anti-goal §18.24 (signal-stream violation by full-iterable
        rendering) — the constraint is "one signal at a time".

        ``field_path`` names WHICH iterable field is streaming — e.g.
        ``"pattern_hash"`` for a ``pattern_map`` panel, ``"url"`` for a
        ``url_set`` panel (pattern_map_and_url_set.md §5). It lets the REPL
        viewer label the ``pattern-map`` / ``urls-panel`` rows (§11.8) and
        peers distinguish a pattern stream from a URL stream on the same card.

        ``ordered`` (STEP-01 / D10) is the card's ordered sampled-chunk
        concept_id list (the same ordered list the §17.14 spine mirror
        already stores). When provided, ``signal_id`` is resolved
        server-side as ``ordered[signal_index]`` (bounded — V5) rather than
        trusting a caller-supplied value; the list itself is stored on the
        entry so ``advance_signal`` can re-resolve on every step without the
        caller re-passing it. When absent, the caller-supplied ``signal_id``
        (or None) is used as-is — backward compatible with pre-STEP-01
        callers (RolloutCoordinator.play/pause/reset).
        """
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            resolved_id = (
                self._resolve_signal_id(ordered, int(signal_index), signal_id)
                if ordered is not None else signal_id
            )
            entry = {
                "card_id":      card_id,
                "total":        int(total),
                "signal_index": int(signal_index),
                "signal_id":    resolved_id,
                "field_path":   field_path or "",
                "paused":       bool(paused),
                "updated_at":   time.time(),
            }
            if ordered is not None:
                entry["ordered"] = list(ordered)
            st.signal_stream[card_id] = entry
            snap = self._stamp(st, workspace_id, "signal_stream")
        self._emit("signal_stream", workspace_id, snap)
        return snap

    def advance_signal(
        self, workspace_id: str, card_id: str, *, step: int = 1,
        field_path: str = "", ordered: Optional[List[str]] = None,
    ) -> UIState:
        """Advance the signal-stream cursor for ``card_id`` by ``step``.

        Wraps around at ``total`` (modulo). If the iterable was paused
        the advance still moves the cursor — pause vs play is a
        separate visibility flag for the RolloutCoordinator's auto-tick
        loop, not a guard on manual advance. A non-empty ``field_path``
        overrides the streamed-field axis label; otherwise the prior
        entry's ``field_path`` is preserved.

        STEP-01 / D10 — after computing ``new_index``, re-resolves
        ``signal_id`` from the ordered sampled-chunk list: either the
        ``ordered`` list passed THIS call, or (more commonly) the list
        already stored on the entry by a prior ``set_signal_stream`` call
        (single source — the caller need not re-pass it every step). When
        no ordered list is available at all, the prior ``signal_id`` is
        PRESERVED (never clobbered to None) — backward compatible with
        existing callers (RolloutCoordinator) that never register one.
        """
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            entry = dict(st.signal_stream.get(card_id) or {})
            total = int(entry.get("total") or 0)
            cur = int(entry.get("signal_index") or 0)
            new_index = (cur + int(step)) % max(total, 1) if total > 0 else cur + int(step)
            active_ordered = ordered if ordered is not None else entry.get("ordered")
            resolved_id = self._resolve_signal_id(
                active_ordered, new_index, entry.get("signal_id"),
            )
            entry.update({
                "card_id":      card_id,
                "total":        total,
                "signal_index": new_index,
                "signal_id":    resolved_id,
                "field_path":   field_path or entry.get("field_path", "") or "",
                "updated_at":   time.time(),
            })
            if ordered is not None:
                entry["ordered"] = list(ordered)
            st.signal_stream[card_id] = entry
            snap = self._stamp(st, workspace_id, "signal_advance")
        self._emit("signal_advance", workspace_id, snap)
        return snap

    def clear_signal_stream(
        self, workspace_id: str, card_id: Optional[str] = None,
    ) -> UIState:
        """Drop one card's signal-stream entry, or all if card_id is None."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            if card_id is None:
                st.signal_stream.clear()
            else:
                st.signal_stream.pop(card_id, None)
            snap = self._stamp(st, workspace_id, "signal_stream_clear")
        self._emit("signal_stream_clear", workspace_id, snap)
        return snap

    def set_rollout_state(
        self, workspace_id: str, *,
        card_id: str = "", field_path: str = "",
        paused: bool = True, signal_index: int = 0, signal_total: int = 0,
        node_id: Optional[str] = None, interval_ms: int = 1000,
        active: bool = True, kind: str = "rollout",
    ) -> UIState:
        """§7.5 / RolloutCoordinator.md §2.4 — set the active rollout summary
        mirror. ``active=False`` clears it (rollout terminated/reset-to-idle).
        ``kind`` tags the emitted ``ui_state_changed`` (``rollout_resumed`` /
        ``rollout_paused`` / ``rollout``)."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            if not active:
                st.rollout_state = None
            else:
                st.rollout_state = {
                    "card_id":      card_id,
                    "field_path":   field_path,
                    "paused":       bool(paused),
                    "signal_index": int(signal_index),
                    "signal_total": int(signal_total),
                    "node_id":      node_id,
                    "interval_ms":  int(interval_ms),
                    "updated_at":   time.time(),
                }
            snap = self._stamp(st, workspace_id, kind)
        self._emit(kind, workspace_id, snap)
        return snap

    def set_node_fold(
        self, workspace_id: str, card_id: str, field_path: str,
        *, expanded: bool = True,
    ) -> UIState:
        """§7.3.4 / object_exploration — toggle an inline node-fold path. A
        right-click on a ``{ref}`` token at ``field_path`` in ``card_id``'s
        field-tree expands it inline (rank-1 reveal) when ``expanded`` else
        collapses it. The per-card ``expanded_paths`` list is the mirror the
        editor renders + the REPL viewer shows."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            entry = st.node_fold_state.get(card_id) or {"expanded_paths": []}
            paths = [p for p in (entry.get("expanded_paths") or []) if p != field_path]
            if expanded and field_path:
                paths.append(field_path)
            if paths:
                st.node_fold_state[card_id] = {
                    "expanded_paths": paths, "updated_at": time.time(),
                }
            else:
                st.node_fold_state.pop(card_id, None)
            snap = self._stamp(st, workspace_id, "node_fold")
        self._emit("node_fold", workspace_id, snap)
        return snap

    def set_dominance_collapse(
        self, workspace_id: str, node_id: str, collapsed: bool,
        *, hidden_set: Optional[List[str]] = None,
        folded_set: Optional[List[str]] = None,
    ) -> UIState:
        """§6.6.5 / §7.3.5 — set/clear the generalized rank-dominance
        collapse for ``node_id`` (Q.3-Q.5).

        On collapse (``collapsed=True``) the dominator's dominated set
        (``folded_set``) folds into it and — in the 3D projector — every
        other visible node (``hidden_set``) is isolated away; only the
        dominator remains. On expand (``collapsed=False``) the entry is
        cleared and the projector animate-loop restores the chunks/nodes
        next frame (fold-state preserved, M.6). The membership sets are
        computed by the route from the dominated-set reachability over the
        ConceptEdge graph + the chunk-url association (rank_dominance.py,
        §8.1.2); this setter only mirrors them.
        """
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            if collapsed:
                st.dominance_collapse[node_id] = {
                    "collapsed":  True,
                    "hidden_set": list(hidden_set or []),
                    "folded_set": list(folded_set or []),
                    "updated_at": time.time(),
                }
            else:
                st.dominance_collapse.pop(node_id, None)
            snap = self._stamp(st, workspace_id, "dominance_collapse")
        self._emit("dominance_collapse", workspace_id, snap)
        return snap

    def set_hover_rect(
        self, workspace_id: str,
        rect: Optional[Dict[str, float]],
    ) -> UIState:
        """Record where the hover preview is currently showing on
        screen. Captured on every mousemove that fires the preview;
        the next pin() reads it as the stick_rect default so the
        pinned panel materialises at the same place."""
        with self._lock:
            st = self._states.setdefault(workspace_id, UIState())
            st.last_hover_rect = dict(rect) if rect else None
            snap = self._stamp(st, workspace_id, "hover_rect")
        self._emit("hover_rect", workspace_id, snap)
        return snap

    def view_state(
        self, workspace_id: str, node_id: str,
    ) -> Dict[str, Any]:
        """Return a one-shot ``{state, collapsed?, …}`` describing this
        node's current UI presentation, per the §UnifiedNodeView model.

        ``state`` is one of: ``hovered`` | ``sticky`` | ``apparition`` |
        ``passive``. The REPL uses this to assert hover/click gestures
        produced the expected view state — without ever needing to
        eval JavaScript in a browser.
        """
        with self._lock:
            st = self._states.get(workspace_id) or UIState()
            pinned = node_id in st.pinned_billboards
            hovered = (st.hovered_id == node_id)
            collapsed = st.pinned_collapsed.get(node_id, True) if pinned else None
        if pinned and hovered:
            state = "sticky+hovered"
        elif pinned:
            state = "sticky"
        elif hovered:
            state = "hovered"
        else:
            state = "passive"
        return {
            "node_id":   node_id,
            "state":     state,
            "collapsed": collapsed,
            "pinned":    pinned,
            "hovered":   hovered,
        }

    def clear_workspace(self, workspace_id: str) -> None:
        """Drop a workspace's UI state — used by ``/api/purge_workspace``."""
        with self._lock:
            self._states.pop(workspace_id, None)
        self._emit("clear", workspace_id, UIState())

    # -- read ------------------------------------------------------------
    def get_state(self, workspace_id: str) -> UIState:
        with self._lock:
            return self._snapshot_locked(workspace_id)

    def list_workspaces(self) -> List[str]:
        with self._lock:
            return list(self._states.keys())

    # -- internals -------------------------------------------------------
    def _snapshot_locked(self, workspace_id: str) -> UIState:
        st = self._states.get(workspace_id) or UIState()
        # Return a *copy* so callers can mutate freely without races.
        return UIState(
            selected_id=st.selected_id,
            hovered_id=st.hovered_id,
            pinned_billboards=list(st.pinned_billboards),
            pinned_collapsed=dict(st.pinned_collapsed),
            last_hover_rect=(dict(st.last_hover_rect) if st.last_hover_rect else None),
            last_stick_rect=(dict(st.last_stick_rect) if st.last_stick_rect else None),
            url_collapsed=dict(st.url_collapsed),
            billboard_url=dict(st.billboard_url),
            compile_expansions={k: dict(v) for k, v in st.compile_expansions.items()},
            halo_focus=(dict(st.halo_focus) if st.halo_focus else None),
            pin_chrome={k: dict(v) for k, v in st.pin_chrome.items()},
            latch_state=dict(st.latch_state),
            viewport_visible_rows=(dict(st.viewport_visible_rows)
                                   if st.viewport_visible_rows else None),
            autocomplete_state=(dict(st.autocomplete_state)
                                if st.autocomplete_state else None),
            editing_field=(dict(st.editing_field)
                           if st.editing_field else None),
            halo_chain=list(st.halo_chain),
            signal_stream={k: dict(v) for k, v in st.signal_stream.items()},
            rollout_state=(dict(st.rollout_state) if st.rollout_state else None),
            node_fold_state={k: dict(v) for k, v in st.node_fold_state.items()},
            dominance_collapse={k: dict(v) for k, v in st.dominance_collapse.items()},
            last_changed_at=st.last_changed_at,
            last_change_kind=st.last_change_kind,
        )

    def _emit(self, kind: str, workspace_id: str, snap: UIState) -> None:
        if self._broadcast is None:
            return
        try:
            self._broadcast(0, {
                "type":         "ui_state_changed",
                "workspace_id": workspace_id or "_default",
                "kind":         kind,
                "state":        snap.to_dict(),
            })
        except Exception:
            # Broadcast is best-effort; never let a downstream queue
            # error break the setter.
            pass


# Singleton wiring (mirrors layout_service / concept_index_service patterns).

_SVC: Optional[UIStateService] = None
_SVC_LOCK = threading.Lock()


def get_ui_state_service(
    *,
    broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> UIStateService:
    """Return the process-wide singleton. ``broadcast`` is set on
    first call; later calls without it preserve the original.
    """
    global _SVC
    if _SVC is not None:
        return _SVC
    with _SVC_LOCK:
        if _SVC is None:
            _SVC = UIStateService(broadcast=broadcast)
    return _SVC
