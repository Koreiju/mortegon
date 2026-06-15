# Retrieval & Sidebar — Result Spine, URL Controls, Visibility

> **Status: realised (cp/*.js); realises §6.4, §8.3, §8.4, §8.5.** The retrieval list + scroll-driven visibility spine is carried by `cp/search.js` (`_setupSpineObserver` → IntersectionObserver flips per-row `chunkCollapseTarget`, firing `/api/ui/viewport_spine` + the `spine_delta` WS — the §8D.18.1 strict spine rule: chunks collapsed-hidden by default, only viewport-visible rows extrude); the URL sidebar + per-URL eye-button is `cp/workspace.js::toggleUrlVisibility` (`/api/ui/url_visibility`). Verified by `viewport-spine-roundtrip`, `spine-delta-emits`, `url-collapse-cascade`, `sticky-starts-collapsed`, `passive-stays-collapsed`.

---

## §1 — Identity

This surface is the 2D control plane for the Real register: a scrollable list of retrieval result rows and a per-URL sidebar, both steel-on-black. Its defining behaviour is the **strict spine rule** (§6.4, §18.12): retrieval chunks are **collapsed-hidden by default**; only chunks for *viewport-visible* result rows (or *pinned-panel-referenced* chunks) are visible in 3D — there is no third path, no global "show all". Scrolling the list is the sole driver of which chunks extrude.

---

## §2 — Structure

Two panels, both `--bg-panel` steel-framed:
- **Result list** — one `.instance-row` per retrieval hit, with an `IntersectionObserver` watching viewport membership.
- **URL sidebar** — one entry per scanned URL with a label, an **eye** button (visibility), an **×** button (purge), and a domain-tree collapse toggle.

**Owns (transient):** the IntersectionObserver; the debounce timer for the viewport set; scroll position. **Reads:** `chunks` (rows + per-URL grouping), `ui.viewport_visible_rows`, `ui.hidden_urls`, `ui.url_collapsed`, `ui.pinned_billboards`.

---

## §3 — Behaviours

1. **Collapsed-hidden by default (§6.4, §8.3, §18.12).** Every retrieval chunk starts folded into its doc-hub. Only viewport-visible rows extrude (`chunkCollapseTarget=0`); off-viewport rows fold back (`=1`). No bulk-expand exists.
2. **Scroll-driven, and only scroll-driven (§8.3).** The `IntersectionObserver` flips the viewport set; a debounced (~120 ms) `ui-viewport-spine` posts the ordered visible chunk ids; the Projector animate loop extrudes them next frame (`projector.md` §5).
3. **URL click is viewport-scoped (§8.4, §18.12).** Clicking a URL label toggles only that URL's doc-hub collapse, scoped to viewport-visible rows when a search is active — it never explodes all nodes.
4. **Eye = visibility flag (§6.3, §18.14).** The eye button flips `hidden_urls`; the Projector writes `scale=0` to that URL's chunks/hubs next frame. Never a mesh mutation.
5. **× = scoped purge (§6.5, §18.4).** The × button purges that URL from the workspace (scoped `purge_workspace`); the store drops its chunks/layout; the scene + sidebar refresh from the frame, not from memory.
6. **Row click = fly + pin (§8.5).** Clicking a `.instance-row` sets `chunkCollapseTarget=0`, tweens the camera to the chunk's 3D position, and pins the unified panel via freeze-at-rect (`billboard.md`). Clicking a `.page-card` flies to the doc-hub, drills into the per-URL instance list, and pins the hub's panel.
7. **Hover = unified panel (§8.6, §18.13).** Hovering any row swaps the **single** `Billboard` (`billboard.md`) — no "root summary", no second widget.

---

## §4 — Composition

| Peer | Through |
|---|---|
| `Projector` (`projector.md`) | spine extrusion; camera fly; visibility flags |
| `Billboard` (`billboard.md`) | row hover preview + row-click pin |
| `Editor` (`editor.md`) | the pinned panels that row-clicks produce |
| `WorkspaceStore` | `chunks`, `ui.viewport_visible_rows`, `ui.hidden_urls`, `ui.url_collapsed` |
| `GestureGateway` | `ui-viewport-spine`, `ui-row-click`, `ui-hover-row`, `ui-url-visibility`, `ui-url-purge`, `ui-domain-toggle` |
| agent perception (§12.1) | `spine-delta` writes the visible-row set to active agents' zone_of_influence |

---

## §5 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Scroll list | `ui-viewport-spine {ordered, total}` | extrude viewport chunks; fold the rest |
| Click result row | `ui-row-click {chunk_id}` | extrude + camera fly + pin |
| Hover row | `ui-hover-row {row_id, chunk_id}` | unified billboard preview |
| Toggle URL collapse | `ui-domain-toggle {url}` | viewport-scoped hub collapse |
| Eye button | `ui-url-visibility {url, hidden}` | flip `hidden_urls` |
| × button | `ui-url-purge {url}` | scoped purge |

---

## §6 — Sequences

### §6.1 Spine (§17.14)
```
scroll → IntersectionObserver fires per row enter/leave
   → debounce ~120 ms → gateway ui-viewport-spine {ordered:[chunk_id…], total}
   → ui_state_changed (viewport_spine) → ui.viewport_visible_rows
   → Projector: chunkCollapseTarget=0 for visible; off-viewport fold back (§6.4)
   → spine-delta → active agents' zone_of_influence (§12.1)
   → REPL viewer retrieval row: "query='X' viewport=N-M of T"
```
### §6.2 Row click fly+pin (§8.5)
```
click .instance-row → ui-row-click {chunk_id}
   → chunkCollapseTarget=0 + camera tween to chunk 3D pos + freeze-at-rect pin
   → ui_state_changed (pinned_billboards + viewport_visible_rows)
```

---

## §7 — Data

**Reads:** `chunks` (grouped by URL), `ui.viewport_visible_rows`, `ui.hidden_urls`, `ui.url_collapsed`, `ui.pinned_billboards`. **Sends:** the §5 gestures. **Receives:** `ui_state_changed`, `purge_workspace` (scoped), `chunk_*`.

---

## §8 — Results

A scroll-driven result list whose viewport rows extrude their chunks in 3D, a URL sidebar with working eye/×/collapse, and fly+pin on row click. Telemetry: `viewport_visible_rows`, `hidden_urls`, `url_collapsed`, `pinned_billboards` (§10.5).

---

## §9 — REPL Mirroring

Feeds the viewer's `retrieval` row (`query='X' viewport=N-M of T`) and, via the spine, the `visible 3D` / `hidden 3D` rows (§11.8). REPL actions `ui-viewport-spine`, `ui-row-click`, `ui-url-visibility`, `ui-url-purge` drive the same extrusion/visibility a user's scroll/click would; the scenario sub-mode accepts inline `s`/`S` scroll and `c <row>` click commands so the operator drives the spine from the terminal (§11.8). The spine is *both* a 3D visibility control and an agent-perception signal (§17.14).

---

## §10 — Theme

Result list + sidebar: `--bg-panel`, `--steel-900` 1px row dividers (structure felt more than seen), labels in `--text-dim` sans, hit text in `--text-primary`. Eye / × / collapse glyphs: `--steel-500`, `--steel-300` on hover; the eye reads "open" vs "hidden" by steel brightness, not colour. Hover row: the row's silver outline brightens (no fill tint, `theme.md` §4). Scrollbar: 6px, `--steel-700` thumb on `--bg-void` track. Everything here is steel-on-black; the only colour is in the 3D chunks the list controls (the exception zone, `projector.md`).

---

## §11 — References

- `DOMAIN_MODEL.md`: §6.4 (strict spine), §8.3 (scroll-spine), §8.4 (sidebar), §8.5 (row click), §8.6 (hover), §6.3 (visibility), §6.5 (purge), §17.14 (spine sequence); anti-goals §18.12/§18.13/§18.14/§18.4.
- Peers: `projector.md`, `billboard.md`, `editor.md`, `scan_streaming.md`.
