# REPL Mirroring — The Symbolic Register's Frontend Obligation

> **Status: realised.** How every frontend surface mirrors into the REPL (the Symbolic register, §14). Realised: `cp/interaction.js::_mirrorUi` POSTs every gesture to a `/api/ui/*` (or `/api/rollout/*`, `/api/apparitions/*`) route; the UIStateService §10.5 mirror holds the canonical state; the `watch-activity` dashboard renders every mirror-field row (incl. `signal`/`rollout`/`apparition`/`node_fold`); and `sim_frontend.py` exercises the same routes so REPL↔frontend are symmetric. The §6 completion bar (gesture row + REPL action + env-scenario + full-smoke + viewer row) is gated by `route-coverage` + `action-registry-coverage` + the 83-scenario `full-smoke`. Each surface doc carries its own §9 slice.

---

## §1 — Identity

The REPL (`scripts/sim_frontend.py`) runs **outside the browser** and is the workspace's **Symbolic register** (§1.5, §14) — the layer of complete transparency over the Real (Projector) and the Imaginary (Editor). The frontend's entire obligation to it is **faithful, complete telemetry**: *what you render, you report.* Every gesture and every render route through the two seams (`gesture_gateway.md`, `frame_bus.md`), and the seams keep the UI State Service mirror (§10.5) in sync, which the REPL reads. The architectural guarantee (`architecture.md` §6): because there is no frontend-only state transition, the REPL can reconstruct the full Imaginary + Real state from frames + telemetry alone.

---

## §2 — The two directions (symmetry)

| Direction | Mechanism |
|---|---|
| **Frontend → REPL** | a view renders → calls `gateway.telemetry(kind, snapshot)` → `/api/ui/telemetry` → UI State Service merges → `ui_state_changed` → REPL viewer reads (§10.5) |
| **REPL → Frontend** | a REPL action hits the same REST route a gesture would (idempotency key) → lifecycle (§10.2) → frames → `FrameBus` → store → every open tab renders |

The two are symmetric by construction: a frontend gesture and the matching REPL action are the *same* REST call producing the *same* frames touching the *same* mirror. Neither side holds a private copy that could diverge (`workspace_store.md` §9).

---

## §3 — The completeness rule (the severance test)

- A **Real or Imaginary state not reflected in the Symbolic is a severance** (§18.1) — a bug.
- A **REPL action that fires without effect on the Real or Imaginary** is also a bug (§14 — the Symbolic has no autonomous content).

Concretely, every view must route mirror-able state through a §10.5 setter (`gateway.telemetry`): a pin → `pinned_billboards` + `pin_chrome` + `last_stick_rect`; a latch → `latch_state`; a scroll → `viewport_visible_rows`; a halo → `halo_focus`; a compile → `compile_expansions`; a signal advance → `signal_stream`; a rollout → `rollout_state`. The §10.5.1 mirror-field roster is the checklist; a view that changes a mirror-able value without a setter call is severed.

---

## §4 — The in-place activity viewer (§14.5 / §11.8)

The REPL's `watch-activity` subcommand renders a **fixed-structure terminal dashboard** that updates **in place** via ANSI cursor codes (`\x1b[<n>A`, `\x1b[2K`) — *dynamic screen update, not infinite-scroll log*. The canonical six base rows (below) plus the realised extension rows (`halo`, `chrome`, `latch`, `spine`, `autocomp`, `editing`, `halochain`, **`signal`**, **`rollout`**, **`apparition`**, `subsystems`) — every §10.5.1 mirror field has a row, so the complex/repeated interactions (iteration, rollout play/pause, multi-frequency retrieval) are visually verifiable through the REPL alone, and the `watch-activity-mirror` env-scenario asserts the backend-mirror → render wiring:

```
─── Workspace Activity (in-place) ─────────────────────────────────────
  scan        | <action> | <progress> | <umap status>
  retrieval   | <query>  | <hit count> | <viewport range> of <total>
  visible 3D  | [chunk:...]                          (<n>/<total>)
  hidden 3D   | [chunk:...]                          (<n>/<total>)
  pinned      | [panel:p_X → chunk:c_Y ("name")]    (<n> pinned)
  compile     | <expansion state>  central=<id>  children=<list>
─────────────────────────────────────────────────────────────────────
```

| Row | Fed by | Frontend source |
|---|---|---|
| `scan` | `chunk_*` counts + `umap_canonical` + `/api/scan-status` | `scan_streaming.md`, `projector.md` |
| `retrieval` | `/api/chunk_search` + `viewport_visible_rows` | `retrieval_and_sidebar.md` |
| `visible 3D` | `viewport_visible_rows.ordered` | `retrieval_and_sidebar.md`, `projector.md` |
| `hidden 3D` | complement against the chunk set | `projector.md` |
| `pinned` | `pinned_billboards` + `pin_chrome` | `concept_view.md`, `editor.md` |
| `compile` | `compile_expansions` | `compile_collapse.md` |
| `halo` (ext) | `halo_focus` | `halo.md` |
| `chrome` (ext) | `pin_chrome` | `concept_view.md`, `editor.md` |
| `latch` (ext) | `latch_state` | `concept_view.md` |
| `spine` (ext) | `viewport_visible_rows` | `retrieval_and_sidebar.md` |
| `autocomp` (ext) | `autocomplete_state` | `field_tree.md` |
| `editing` (ext) | `editing_field` | `field_tree.md` |
| `halochain` (ext) | `halo_chain` | `halo.md` |
| `signal` (ext) | `signal_stream` | `pattern_map_and_url_set.md`, `agent_and_rollout.md` |
| `rollout` (ext) | `rollout_state` | `agent_and_rollout.md` (`RolloutCoordinator`) |
| `apparition` (ext) | `/api/apparitions/mode` | `halo.md` (§8.1.1 single/multi-frequency) |
| `subsystems` (ext) | `/api/subsystem_status` | (no-mocks contract §13) |

Bounded lines; identifier abbreviation after first occurrence; multi-line values flattened with `↩`. Last-write-wins per field. The viewer reads only WS broadcast + low-cadence REST polls, never the DB directly. **New observable state extends an existing row; it never spawns a parallel log stream** (§14.4.4).

---

## §5 — Behaviours

1. **What renders is reported (§3).** Every view calls a §10.5 setter for any mirror-able change.
2. **No frontend-only state (§1).** Every transition round-trips through the backend, so the REPL never misses one.
3. **Idempotency parity (§14.3).** A frontend gesture and a REPL action carry the same idempotency semantics; replays are safe.
4. **In-place, not scroll (§4).** The viewer is a dynamic dashboard; the frontend feeds it field updates, not log lines.
5. **Symbolic self-similarity (§14).** The viewer adopts the same steel-and-black restraint (`theme.md` §9) so the Symbolic looks like the Imaginary it mirrors (transcendental permanence).

---

## §6 — Activities & Sequences

Every gesture in `gesture_gateway.md` §5 has a REPL action of the same name and a viewer effect; the verification loop (§14.1):
```
REPL action  →  REST (idempotency key)  →  lifecycle (§10.2)  →  WS frame  →  frontend renders
                                                                      │
                                                                      ▼
                                                         UI State mirror (§10.5)
                                                                      │
                                                                      ▼
                                                         in-place viewer refreshes (in place)
   ⟂ frontend gesture  →  same REST  →  same frames  →  telemetry  →  same mirror  →  same viewer
```

---

## §7 — Data

**Out (frontend → mirror):** `/api/ui/telemetry` batches keyed by §10.5 field. **In (mirror → frontend):** `ui_state_changed` (full snapshot) via `FrameBus`. **Viewer reads:** WS frames + `/api/scan-status`, `/api/chunk_search`, `/api/subsystem_status` polls.

---

## §8 — Results

A terminal mirror that is a faithful, in-place representation of the live Real + Imaginary state, drivable in both directions. The frontend's contribution: complete telemetry such that no surface state is invisible to the REPL.

---

## §9 — The acceptance bar (frontend)

A frontend feature is complete when (§14.4): (1) its gesture exists as a `gesture_gateway.md` kind = a §14.2 catalogue row with a REPL action; (2) an env-scenario asserts the REPL→backend→frame→render→telemetry round-trip; (3) `full-smoke` passes in real-stack and stub mode; (4) the viewer reflects the observable state with no new log stream. **A screenshot is never proof** (§2.9, §14) — the REPL round-trip is. This architecture makes the bar reachable because every gesture and every render route through the two seams.

---

## §10 — Theme

The viewer adopts the theme's restraint in the terminal (`theme.md` §9): dim rule-lines `─` (the analogue of `--steel-900` dividers), `--text-primary`-equivalent values, `--text-dim`-equivalent labels, and the single `--accent-error` red for error envelopes — no other colour. The Symbolic register is visually self-similar to the steel-on-black Imaginary it mirrors.

---

## §11 — References

- `DOMAIN_MODEL.md`: §14 (REPL two-way feedback), §14.1 (verification loop), §14.2 (gesture catalogue), §14.4 (acceptance bar), §14.5 / §11.8 (in-place viewer), §10.5 / §10.5.1 (mirror roster), §13 (no-mocks / subsystems); anti-goal §18.1 (severance).
- `code_constraints/repl_actions.md`, `code_constraints/env_scenarios.md`.
- Peers: **every** suite doc's §9 *REPL mirroring* section; `gesture_gateway.md`, `workspace_store.md`, `frame_bus.md`.
