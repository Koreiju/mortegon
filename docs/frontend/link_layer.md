# LinkLayer — Solid Links & The 2D↔3D Arrow

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §7.3.** The line-drawing role is carried by `cp/edge_manager.js` (3D edge lines over `initialNodeData` positions) + `cp/concept_graph.js::_drawConceptEdges` / `_edgeStyleForType` (2D concept edges — solid undirected silver, **no arrowheads/dashes** §O.16, the structural guard against §18.7) + the solid yellow `#ffd700` 2D↔3D connector. Verified by `edge-roundtrip` (+ the arrowhead-free SVG audit in the gesture scenarios).

---

## §1 — Identity

`LinkLayer` is one SVG layer beneath the Editor's panels. It draws three things and nothing else: **hard links** (the commitment fan), **soft links** (the possibility ring), and the **2D↔3D link arrow**. Because it is the sole line-drawer, the no-dashes rule (§18.7) is enforced at one object: **no element here ever carries `stroke-dasharray`.** The hard/soft distinction is by stroke brightness + weight + arrowhead glyph (§3.2.1), within the steel palette; the 2D↔3D arrow is the one saturated stroke (`--accent-arrow` yellow).

---

## §2 — Structure

A single `<svg>` layer in the Editor (`editor.md`), z-ordered beneath panels. **Owns (transient):** the per-frame projected screen point of each pinned panel's 3D node (for the arrow); the in-progress wire path during a drag. **Reads:** `edges` (hard links), `ui.halo_focus.candidates` (soft links), `ui.compile_expansions` (stringless compile edges), `ui.pinned_billboards` + the Projector's per-frame projection (for the 2D↔3D arrow target).

---

## §3 — Behaviours

1. **No dashes, ever (§18.7, frontend_rendering §1.6/§2.3).** Every stroke is solid. The hard/soft distinction is **never** a dash pattern.
2. **Hard link = commitment fan (§3.2.1).** Solid `--steel-300` (≈full brightness) **undirected line**, ~2px, **no arrowhead** (§O.16); drawn from `edges`. Fans outward to committed targets.
3. **Soft link = possibility ring (§3.2.1).** Solid `--steel-700` (≈40% brightness) **undirected line**, ~1px, **no arrowhead** (§O.16); drawn from `ui.halo_focus.candidates`; sits concentric at the halo radius (`halo.md`). Vanishes when the halo closes (it lives in the apparition cache, not in `edges`).
4. **Stringless compile edges (§7.3).** Plain solid `--steel-700` lines between a compiled central node and its children, **no per-edge text labels** (`compile_collapse.md`).
5. **The 2D↔3D arrow is solid yellow (§18.7).** `stroke="#ffd700"` (`--accent-arrow`), `stroke-width="2"`, solid, from a pinned panel to its chunk's projected screen point; updated **per frame** from the 3D node's projected position. Off-frustum → `display:none` (no dashed placeholder). It **drives nothing** — it does not move the panel (§6.6.2, §18.31).
6. **Edge-type by weight + brightness, not hue or arrowhead (`theme.md` §2.4).** Where §3.2 edge types must differ visually, the difference is **stroke weight + brightness** within steel — **no arrowhead** (undirected, §O.16) — never a saturated colour (preserving the dark-minimal palette). A type-mismatch edge tints `--accent-error` (the one warning hue, §9.8).

---

## §4 — Composition

| Peer | Through |
|---|---|
| `Editor` (`editor.md`) | hosts the SVG layer beneath panels |
| `Halo` (`halo.md`) | supplies soft-link candidates (possibility ring) |
| `Projector` (`projector.md`) | supplies the per-frame projected screen point for the arrow |
| `compile_collapse.md` | supplies the stringless compile edges |
| `WorkspaceStore` | `edges`, `ui.halo_focus`, `ui.compile_expansions`, `ui.pinned_billboards` |

---

## §5 — Activities & §6 Sequences

LinkLayer has no gestures of its own; it draws what the store + the per-frame projection dictate, and it re-routes on the Pulse budget.

```
per animate frame (liveness.md §5):
   for each pinned panel with data-3d-node-id:
      p = Projector.project(node.world_pos)
      if p in frustum: draw yellow arrow panel→p (solid, 2px); else arrow.display=none
   hard links (edges): solid --steel-300 2px line, no arrowhead, on the commitment fan (re-route eased on change)
   soft links (halo_focus.candidates): solid --steel-700 1px line, no arrowhead, on the possibility ring
   compile edges (compile_expansions): solid --steel-700 1px stringless

on concept-edge-create (soft→hard promotion): the soft stroke is removed; a hard stroke is added (eased)
```

---

## §7 — Data

**Reads:** `edges`, `ui.halo_focus.candidates`, `ui.compile_expansions`, `ui.pinned_billboards`; the Projector's per-frame projection. **Sends:** nothing (wiring gestures originate in the Editor/Halo). **Receives (indirectly):** `concept_changed` (edges), `ui_state_changed` (halo/compile/pins).

---

## §8 — Results

A solid-line link graph: bright steel hard fans, dim steel soft rings, stringless steel compile edges, and a single solid yellow line per pinned panel tracking its 3D node. **No dashes and no arrowheads anywhere** (§O.16); links are undirected. Telemetry: edges are concept state (`concept_changed`); soft links + arrow are derived render state (no separate mirror field).

---

## §9 — REPL Mirroring

Hard links are concept truth: `concept-edge-create` (REPL or frontend) → `concept_changed`×2 → `edges` slice → LinkLayer draws the fan in every tab. Soft links have no mirror field (they live in the apparition cache, §3.2.1) but their *source* — `halo_focus.candidates` — is mirrored (`halo.md` §9), so the REPL can reconstruct what the possibility ring shows. The 2D↔3D arrow is pure render derived from `pinned_billboards` + layout; its correctness (solid yellow, tracks the node, no dashes) is asserted by the no-dashed-lines and arrow-tracking env-scenarios (§18.7).

---

## §10 — Theme

This object *is* a theme-critical surface. Hard links `--steel-300`/2px/filled; soft links `--steel-700`/1px/hollow; compile edges `--steel-700`/1px/stringless — all solid, all steel, brush-consistent. The **only** non-steel stroke in the entire 2D interface is the `--accent-arrow` yellow 2D↔3D arrow (`theme.md` §2.4), mandated by §18.7. Type-mismatch edges tint `--accent-error`. There are no glows, no dashes, no colour-coded edge palette; differentiation is brightness + weight + arrowhead glyph.

---

## §11 — References

- `DOMAIN_MODEL.md`: §3.2 (edge types), §3.2.1 (hard/soft, fan/ring), §7.3 (stringless edges), §6.6.2 (separation); anti-goals §18.7/§18.31.
- Peers: `editor.md`, `halo.md`, `projector.md`, `compile_collapse.md`.
