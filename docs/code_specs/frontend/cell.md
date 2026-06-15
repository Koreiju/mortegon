# Spec — Frontend / Cell (ConceptView · FieldTree · field_strategies)

> Deepens [`code_architecture/frontend/cell.md`](../../code_architecture/frontend/cell.md). Modules: `fe/cell/{concept_view,field_tree,field_strategies}.ts`. Types: [`../types.md`](../types.md) §2 (`UiMode`, `BraceState`). The data-self-defining renderer.
>
> **Realized form (cp/*.js).** Greenfield `fe/cell/*.ts`; realized in `cp/concept_graph.js` (`_createConceptCard`, `_fieldTreePrint` JSON-or-passthrough, `_growRow` plus-signs, `_pythonNativeTypedView`) + `cp/billboard.js` (the pinned panel) — see `frontend/{concept_view,field_tree,object_exploration}.md`. The `field_strategies.ts` 5-strategy parse is greenfield (realized: JSON + passthrough only, field_tree.md §3). Verified via `edit-field-roundtrip`, `node-fold-roundtrip`, `unified-node-view-states`.

---

## §1 — `FieldTree`

```ts
type FieldNode = { key: string; value: string; children: FieldNode[]; path: string;
                   meta: { ref?: Slug; type?: string; attr?: string; cypher?: boolean; iterable?: boolean; readonly?: boolean; brace?: BraceState } };
class FieldTree {
  static parse(raw: string): FieldNode               // detect-and-parse (field_strategies)
  static print(tree: FieldNode): string              // pure-print, NO syntax glyphs
  static project(tree: FieldNode, mode: UiMode): HTMLElement
  static serialize(tree: FieldNode): string          // canonical pure-print → PATCH
}
```
- **`parse`** — try `field_strategies` in order, first match wins: `Json → BracketList → IndentTree → Html → PlainText`. Structure is rebuilt **fresh per render** (no persistent schema — "data is the schema"). Detect markers: `{slug}`→`meta.ref`; `key: Type = v`→`meta.type`; cypher literal→`meta.cypher`; iterable root + external ref→`meta.iterable` (§O.19); `{}`-beside-spaced-key→field on-ramp.
- **`print`** — `key: value`, **tab-indented** nesting, no JSON braces/quotes ever shown. **Key-value vs multiline** inferred by consistent tabs (§O.20): a value that is a tab-indented block → multiline (key is the block's primary key); else key-value.
- **`serialize`** — canonical pure-print; the PATCH `data` body (spine.md `send`).

```ts
// field_strategies.ts — each: detect(raw): boolean; parse(raw): FieldNode; 
const STRATEGIES = [JsonStrategy, BracketListStrategy, IndentTreeStrategy, HtmlStrategy, PlainTextStrategy];
```

---

## §2 — `ConceptView`

```ts
class ConceptView { static render(node: ConceptNode, mode: UiMode, hostRect?: Rect): HTMLElement }
```
- **One DOM routine; modes elide (§18.11 — never a fork):**
  - `PANEL` — canonical rows (`name`,`description`,`value`=field-tree,`compiled`) + user rows via `+→`(child)/`+↓`(sibling); empty rows hidden; **latch** slides the data block out as an **equal-height** side panel (§4.4); form-fit to content.
  - `COLLAPSED` — billboard: name + description + rendering only.
  - `PHANTOM` — **name only** (halo); scores in slow-hover tooltip from `index` slot.
  - `CHILD` — **value only** (name implicit from position); multiline expands the box.
- **Affordances** — `×` delete omitted when `node.backing` is `fixture::*` or `node.meta.readonly` (🔒). Click-to-edit = borderless single-left (imaginary.md gesture); edits `serialize`→`send`.
- **Singular-primitive aspect (§O.19)** — `isSingularPrimitive(node)` decides node-vs-panel: a singular field → a graph node; an aggregate → a panel that compiles to a graph. Drives whether `imaginary.md` shows it as a node or a containment panel.
- **Autocomplete** — typing in a new row's name field queries `/api/concept_completions`; selecting inserts `{<linked_name>}` into the value (typed-linking on-ramp); writes `autocomplete_state` via gateway.

---

## §3 — Excluded
Theme tokens (border/glyph/`frontend/theme.md`); the compile *backend* (compute.md). `FieldTree.parse/print` mirror the backend `FieldTree` used in compute.md §1 — same grammar, two runtimes (the client prints/edits; the backend compiles).
