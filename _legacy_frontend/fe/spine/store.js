/**
 * fe/spine/store.js — WorkspaceStore: the normalized single source of truth.
 *
 * Canonical state mutates ONLY via applyFrame() (called by FrameBus) and the
 * REST read hydrators. Views never write canonical state; they subscribe and
 * render. Optimistic gesture echoes live in a separate overlay slice that a
 * real frame supersedes. (code_specs/frontend/spine.md §1)
 *
 * Frame contract: backend/api/ws_frames.py. Every frame is
 *   { type, frame_seq, workspace_id?, ...body }.
 */

export class WorkspaceStore {
  constructor() {
    this.slices = {
      concepts: new Map(),     // concept_id -> ConceptNode
      edges: new Map(),        // edge_id -> ConceptEdge
      index: new Map(),        // concept_id -> { pagerank, similar_to, provenance, embedding? }
      layoutCoords: new Map(), // id -> [x,y,z,h,s,v]
      urlRoots: new Map(),     // url -> { root_position, bounding_radius }
      provenance: new Map(),   // id -> provenance class
      chunks: new Map(),       // chunk id -> chunk record
      apparitions: new Map(),  // focal_id -> [candidate]
      tokens: new Map(),       // parameter_card_id -> string buffer
      evolution: [],           // EditDiff[]
      ui: {},                  // last /ui/state snapshot
      seq: 0,                  // last applied frame_seq (per active WS)
    };
    this.overlay = new Map();  // "slice:key" -> value (optimistic echo)
    this._subs = new Set();    // { selector, cb, last }
  }

  /** Subscribe with a selector; cb(next, changedKinds) fires on relevant change. */
  subscribe(selector, cb) {
    const entry = { selector, cb, last: undefined };
    this._subs.add(entry);
    try { entry.last = selector(this.slices); } catch { entry.last = undefined; }
    return () => this._subs.delete(entry);
  }

  _notify(changedKinds) {
    for (const e of this._subs) {
      let next;
      try { next = e.selector(this.slices); } catch { continue; }
      if (next !== e.last) { e.last = next; try { e.cb(next, changedKinds); } catch (err) { console.error('[store sub]', err); } }
    }
  }

  /** Optimistic echo (cleared when the authoritative frame arrives). */
  echo(slice, key, value) { this.overlay.set(`${slice}:${key}`, value); this._notify(new Set([slice])); }
  clearEcho(slice, key) { this.overlay.delete(`${slice}:${key}`); this._notify(new Set([slice])); }

  read(slice) { return this.slices[slice]; }

  /** Apply one WS frame. Returns the set of changed slice kinds. */
  applyFrame(frame) {
    if (!frame || typeof frame !== 'object') return;
    // Monotone ordering within a connection: discard stale frames.
    const fs = frame.frame_seq;
    if (typeof fs === 'number') {
      if (fs <= this.slices.seq && fs !== 0) { /* allow seq 0 bootstraps */ }
      this.slices.seq = Math.max(this.slices.seq, fs);
    }
    const changed = new Set();
    switch (frame.type) {
      case 'umap_canonical': {
        const { coords = {}, url_roots, removed_ids, provenance } = frame;
        for (const [id, vec] of Object.entries(coords)) this.slices.layoutCoords.set(id, vec);
        if (url_roots) for (const [u, r] of Object.entries(url_roots)) this.slices.urlRoots.set(u, r);
        if (provenance) for (const [id, p] of Object.entries(provenance)) this.slices.provenance.set(id, p);
        if (removed_ids) for (const id of removed_ids) { this.slices.layoutCoords.delete(id); this.slices.provenance.delete(id); }
        changed.add('layout');
        break;
      }
      case 'concept_index_update': {
        const { updates = {}, removed_ids } = frame;
        for (const [id, slot] of Object.entries(updates)) this.slices.index.set(id, slot);
        if (removed_ids) for (const id of removed_ids) this.slices.index.delete(id);
        changed.add('index');
        break;
      }
      case 'concept_changed': {
        const { concept_id, change, concept } = frame;
        if (change === 'deleted') this.slices.concepts.delete(concept_id);
        else if (concept) this.slices.concepts.set(concept_id, concept);
        this.clearEcho('concepts', concept_id);
        changed.add('concepts');
        break;
      }
      case 'edge_changed': {
        const { edge_id, change, edge } = frame;
        if (change === 'deleted') this.slices.edges.delete(edge_id);
        else if (edge) this.slices.edges.set(edge_id, edge);
        changed.add('edges');
        break;
      }
      case 'chunk_added':
      case 'chunk_replaced': {
        const c = frame.chunk || frame;
        const id = c.chunk_id ?? c.id ?? frame.chunk_id;
        if (id != null) { this.slices.chunks.set(String(id), c); changed.add('chunks'); }
        break;
      }
      case 'chunk_removed': {
        const id = frame.chunk_id ?? frame.id;
        if (id != null) { this.slices.chunks.delete(String(id)); changed.add('chunks'); }
        break;
      }
      case 'apparition_hint': {
        if (frame.focal_id) { this.slices.apparitions.set(frame.focal_id, frame.candidates || []); changed.add('apparitions'); }
        break;
      }
      case 'agent_token': {
        const k = frame.parameter_card_id || '';
        this.slices.tokens.set(k, (this.slices.tokens.get(k) || '') + (frame.token || ''));
        changed.add('tokens');
        break;
      }
      case 'evolution_log_diff': {
        if (frame.diff) { this.slices.evolution.push(frame.diff); changed.add('evolution'); }
        break;
      }
      case 'purge_workspace': {
        const { urls } = frame;
        if (urls && urls.length) {
          // URL-scoped purge: drop coords/chunks whose url matches.
          for (const u of urls) this.slices.urlRoots.delete(u);
        } else {
          this.slices.layoutCoords.clear(); this.slices.urlRoots.clear();
          this.slices.chunks.clear(); this.slices.provenance.clear();
          this.slices.concepts.clear(); this.slices.edges.clear();
          this.slices.index.clear(); this.slices.apparitions.clear();
        }
        changed.add('layout'); changed.add('chunks'); changed.add('concepts');
        break;
      }
      case 'stats': case 'log': case 'done': case 'cached':
      case 'chunks_partial': case 'instances_indexed': case 'nodes':
        // progress / telemetry frames — surfaced via the activity row, no slice mutation here.
        changed.add('progress');
        break;
      default:
        // Unknown frame types are ignored (forward-compatible).
        break;
    }
    if (changed.size) this._notify(changed);
    return changed;
  }

  /** Bulk-hydrate the concepts slice from a REST list (GET /api/concepts). */
  hydrateConcepts(list) {
    for (const c of list || []) this.slices.concepts.set(c.concept_id, c);
    this._notify(new Set(['concepts']));
  }

  resetAll() {
    for (const k of ['concepts','edges','index','layoutCoords','urlRoots','provenance','chunks','apparitions','tokens']) this.slices[k].clear?.();
    this.slices.evolution = []; this.slices.seq = 0; this.overlay.clear();
    this._notify(new Set(['concepts','layout','chunks','index']));
  }
}
