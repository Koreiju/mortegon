# Frontend — Cell (ConceptView · FieldTree · field_strategies)

> **Owns:** the one record renderer (four modes) + the data-self-defining field-tree interpreter. Modules: `fe/cell/concept_view.ts`, `field_tree.ts`, `field_strategies.ts`. Design: §4.2 / §4.4 / §4.6 / §4.6.1 / §9.6.1 / §O.19 / §O.20 / §18.11 + `frontend/{concept_view,field_tree,compile_collapse}.md`. Realises `code_constraints/frontend_rendering.md`.

---

## §1 — Responsibility

Render **one** ConceptNode anatomy in **four modes** — `panel` (full), `collapsed` (billboard), `phantom` (halo, name-only), `child` (compiled subgraph, value-only) — through **one DOM routine** that elides per mode (never a fork, §18.11). Interpret the `data` field as a **syntax-agnostic tree** (the data block dissolved; "data is the schema") and round-trip it: parse → print → project → edit → serialize.

---

## §2 — Public Surface

```ts
// concept_view.ts
ConceptView.render(node, mode: 'panel'|'collapsed'|'phantom'|'child', hostRect?): DOM

// field_tree.ts
FieldTree.parse(raw: string): FieldNode          // detect-and-parse; strategies in field_strategies.ts
FieldTree.print(tree): string                    // pure-print (key:value, tab nesting, NO syntax glyphs)
FieldTree.project(tree, mode): DOM
FieldTree.serialize(tree): string                // canonical pure-print → PATCH via gateway

// FieldNode
type FieldNode = { key, value, children: FieldNode[], path, meta: { ref?, type?, attr?, cypher?, iterable?, readonly? } }
```

---

## §3 — Internal Logic

### §3.1 FieldTree — data is the schema (§4.2)
Structure is parsed **fresh per render** — no persistent schema object. `field_strategies.ts` holds detectors tried in order (first match wins): `Json | BracketList | IndentTree | Html | PlainText`. `print` is **pure**: `key: value`, tab-indented nesting, **no JSON/syntax glyphs ever surface** to the user.
- **Type slot** (§9.6.1): `key: Type = value` — the type annotation renders inline (the materialised python-API form, materialiser.md).
- **Key-value vs multiline inferred by consistent tabs** (§O.20): a field whose value is a tab-indented block is multiline (its key is the primary key to the block); otherwise key-value. The `{}` empty-brace beside a spaces-containing key is the **field on-ramp** (start a new field).
- **Iteration ⟺ external `{ref}`** (§O.19): a `{ref}` into an iterable rooted at a base node marks `meta.iterable`; signal-stream renders **one instance at a time** (§4.6.1) from the current sample index (the `signal_stream` UIState slot, mirrored).

### §3.2 ConceptView — one anatomy, modes elide (§18.11)
The canonical rows (`name, description, value(=field-tree), compiled`) are `FieldTree` rows with reserved slugs; user rows add via horizontal `+→` (child) / vertical `+↓` (sibling). Modes:
- `panel` — all rows + latch + form-fit; empty rows hide; **latch slides the data block out as an equal-height side panel** (§4.4).
- `collapsed` — billboard content (name + description + rendering only).
- `phantom` — **name only** (halo; scores live in slow-hover tooltips).
- `child` — **value only** (name implicit from structural position; multiline expands the box).
- The `×` delete affordance is omitted for the four fixtures + read-only python-native nodes (🔒, materialiser.md).

### §3.3 Edit + the singular-primitive aspect (§O.19)
Click-to-edit via hidden-overlay buttons (borderless single-left-click); Tab / Shift-Enter markdown handlers (§O.20). **The singular-primitive aspect decides kind:** a singular-field primitive **IS a graph node**; an aggregate **is a knowledge panel** that compiles to a graph. Autocomplete in a new row's name field binds to existing concept names by inserting `{<linked_name>}` into the value (the typed-linking on-ramp). Serialized edits PATCH through the gateway (spine.md); the echo clears when the `concept_changed` frame returns.

---

## §4 — Dependencies

- **Calls:** `GestureGateway.send` (edits, fold, compile), the store (read the node + its index slot).
- **Called by:** every surface that shows a node — `Billboard` (collapsed), `Halo` (phantom), `Editor` (panel + child), the side panel.

---

## §5 — Excluded

- The theme tokens (border/glyph rendering — `frontend/theme.md`); the compile *backend* logic (compute.md). This is the renderer + interpreter, not the compiler.
