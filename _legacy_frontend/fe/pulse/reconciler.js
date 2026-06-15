/**
 * fe/pulse/reconciler.js — keyed enter/update/exit diff.
 *
 * Minimal mutation: adding the 501st item never touches the first 500.
 * Keys are stable (integer chunk_id, concept_id). An update whose target is
 * an open-edit field is a no-op (edit-safety). (code_specs/frontend/pulse.md §1)
 */

export class Reconciler {
  /** diff(nextKeys:Iterable, prevKeyset:Set) -> {enter, update, exit} */
  static diff(nextKeys, prevKeyset) {
    const next = nextKeys instanceof Set ? nextKeys : new Set(nextKeys);
    const enter = [], update = [], exit = [];
    for (const k of next) (prevKeyset.has(k) ? update : enter).push(k);
    for (const k of prevKeyset) if (!next.has(k)) exit.push(k);
    return { enter, update, exit };
  }

  /** Apply a diff against a live map of view handles. */
  static apply(map, next, handlers) {
    const prev = new Set(map.keys());
    const { enter, update, exit } = Reconciler.diff(next.keys(), prev);
    for (const k of exit) { handlers.onExit?.(k, map.get(k)); map.delete(k); }
    for (const k of enter) { const h = handlers.onEnter?.(k, next.get(k)); if (h !== undefined) map.set(k, h); }
    for (const k of update) { if (handlers.isEditing?.(k)) continue; handlers.onUpdate?.(k, next.get(k), map.get(k)); }
    return { enter, update, exit };
  }
}
