# Compile / Collapse — The Dialectical Inversion

> **Status: realised (cp/*.js); greenfield form in `FRONTEND_REDESIGN.md` §4.3 / §6.5.** The synthesis↔analysis toggle is carried by `cp/billboard.js::_togglePanelCompileExpand` (double-left on the panel) firing `/api/ui/compile_expand` / `compile_collapse` (mirror `compile_expansions`); the symmetric collapse restores the panel. Right-click is the inline type-graph fold (`node_fold`, `object_exploration.md`). The compile itself fuses forward + closest-inverse (`/api/conceptual/compile`). Verified by `ui-collapse-toggle`, `compile-fuses-inverse`.

---

## §1 — Identity

A **double-left-click** on a `panel`-mode `ConceptView` body (not a textarea) toggles the **dialectical inversion** (§7.3) between two representations of the same ConceptNode: the **panel** (synthesis — the node as one semantic unit) and the **subgraph** (analysis — the node decomposed into one child per top-level data key or `{var}` reference). The toggle is symmetric in both directions: a double-left-click on a panel converts it to graph form, and on a graph node converts it back to its containment panel (right-click is instead the rank-1 inline type-graph fold, in the knowledge-panel form, §7.3.4 / `object_exploration.md`). The frontend renders the toggle; the backend computes the decomposition. The underlying record is untouched on either flip.

---

## §2 — Structure

The feature is not its own object; it is a behaviour of `ConceptView` (the views) + `Editor` (the layout) + `LinkLayer` (the stringless edges) driven by the `ui.compile_expansions` mirror field. **State read:** `ui.compile_expansions[central_id] = {children:[ids], expanded_at}`. **Children:** each is a `child`-mode `ConceptView` (value-only, form-fit) created on the backend keyed `<card_id>__<key>`.

---

## §3 — Composition

| Peer | Through |
|---|---|
| `ConceptView` (`concept_view.md`) | the central `panel` and the `child` views |
| `Editor` (`editor.md`) | ray-constrained child layout around the focal |
| `LinkLayer` (`link_layer.md`) | the stringless edges between central and children |
| `Halo` (`halo.md`) | children carry their own halos (§8.2.3) |
| `GestureGateway` | `ui-compile-expand` / `ui-compile-collapse` |
| backend compile (§7.1) | decomposes keys, resolves `{var}`, runs cypher, prints rendering |

---

## §4 — Behaviours

1. **Symmetry is the contract (§7.3).** Double-left-click a panel → graph form; double-left-click a graph node → its containment panel. Same gesture, inverse effect, in both representations. (Right-click is **not** this toggle — it is the rank-1 inline type-graph reveal in the knowledge-panel form; the graph reveals the same rank-1 walk via hover-preview + click instead, in node-count parity with the panel, §O.1 / §7.3.4 / `object_exploration.md`; the gesture moved off right-click in the M.7 update.)
2. **Brace-reveal works in both forms; graph mirrors the panel's node set (§O.1).** Graph form draws the singular-field nodes the panel currently shows, joined by **undirected line links** (node-count parity), with no *independent* fold state. Braces mark hidden rank-1 links in **both** forms: in the panel, right-click unfolds inline; in the graph, **hover previews** and a **click instantiates the rank-1 walk**. A `{ref}` to an already-visible node resolves to a solid link; a `{ref}` to a hidden node keeps its braces (§O.1a). A double-left-click on a graph node returns it to its containment panel.
3. **Children are full ConceptViews (§8.2.3).** They carry the same hover/click/halo/right-click affordances as any panel — because they *are* the same renderer (`concept_view.md`).
4. **Stringless edges (§7.3).** Child edges are plain solid lines, no per-edge text labels (`link_layer.md`).
5. **Record untouched.** Expand creates child ConceptNodes; collapse deletes them; the central record's `data` is unchanged on either flip.
6. **Read-only variant (§7.3 / §9.6).** When the central is python-native, children render desaturated + 🔒, values non-editable; collapse still works.
7. **Compile is lazy reveal-as-it-walks (§O.9).** Expanding/running follows `{ref}`s on demand as the walk reaches them, revealing each in the GUI as it is walked (DOMAIN §7.1); the reveal mechanic and the compile traversal are the *same* walk. A background cascade recomputes values but does not auto-unfold (§O.13).

---

## §5 — Activities & §6 Sequences

| Activity | Gesture | Effect |
|---|---|---|
| Expand | `ui-compile-expand {card_id}` | backend compiles + decomposes → children render |
| Collapse | `ui-compile-collapse {card_id}` | backend deletes children → panel restores |

```
EXPAND:  double-left-click panel body
   → gateway ui-compile-expand {card_id}
   → backend: ConceptComputeNode.compile (§7.1)  [resolve {var}; run cypher (§7.1.4); decompose top-level keys → child creates keyed <card_id>__<key>]
   → concept_changed × N (children) + ui_state_changed (compile_expansions[card_id]=children)
   → FrameBus → store → Editor lays children ray-constrained around focal; each = ConceptView('child', …)
   → LinkLayer draws stringless edges
   → REPL viewer compile row: "EXPANDED central=p_X children=[url, xpath, html_raw, …]"

COLLAPSE: double-left-click central node
   → gateway ui-compile-collapse {card_id}
   → backend deletes child concepts (§10.2) → concept_changed × N + cleared compile_expansions
   → Editor dissolves child views (Reconciler exit, liveness.md §1); panel restores
```

---

## §7 — Data

**Reads:** `ui.compile_expansions`, the child `concepts[<card_id>__<key>]`. **Sends:** `ui-compile-expand` / `ui-compile-collapse`. **Receives:** `concept_changed`×N + `ui_state_changed`. The decomposition (which keys become children, the `{var}` resolution, the cypher execution) is entirely backend (§7.1); the frontend renders the result.

---

## §8 — Results

Expanded: a central node with value-only children fanned around it, stringless solid edges, each child form-fit and individually interactive. Collapsed: the original panel restored. Telemetry: `compile_expansions[card_id]` populated/cleared (§10.5).

---

## §9 — REPL Mirroring

`compile_expansions` is a §10.5 mirror field and the dedicated `compile` row of the in-place viewer (§11.8): `EXPANDED central=p_X children=[…]`. The REPL drives the dialectic identically via `ui-compile-expand`/`ui-compile-collapse` actions (§14.2) — a REPL expand renders children in every open tab; a frontend expand updates the viewer row. Symmetric round-trip (`repl_mirroring.md`).

---

## §10 — Theme

Central panel: standard `concept_view.md` steel-on-black. Children (`child` mode): `--bg-panel` boxes, `--steel-700` hairline, value in monospace `--text-primary`, form-fit to the value. Stringless edges: `--steel-700` 1px solid (no dashes, §18.7; no text labels). On hover a child brightens its border to `--steel-300` and may open a halo (steel rings, `halo.md`). Read-only children: `--steel-900` border, 🔒 `--text-lock`. The expand/collapse motion is an eased ray-fan-out / fold-in over the Pulse budget (`liveness.md` §2) — no colour, just steel boxes sliding along their rays.

---

## §11 — References

- `DOMAIN_MODEL.md`: §7.3 (dialectical inversion), §7.3.1/§7.3.2 (subgraph layout), §7.1 (compile), §8.2.3 (child halos), §9.6 (read-only variant), **§7.3.5 (the generalized rank-dominance collapse — a *distinct* gesture from this double-left compile toggle: right-click on a dominator folds its rank-dominance set and, in 3D, isolates it, §6.6.5; Q.3–Q.5)**.
- Feature doc: [`../features/compile_collapse_dialectic.md`](../features/compile_collapse_dialectic.md).
- Peers: `concept_view.md`, `field_tree.md`, `editor.md`, `link_layer.md`, `halo.md`.
