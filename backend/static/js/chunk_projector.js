/**
 * chunk_projector.js — ES module entry point.
 *
 * This file is intentionally thin: it declares the ChunkProjector class
 * (constructor + static members) and then assembles it by mixing in the
 * focused modules from ./cp/.  Each cp/ module exports a plain object whose
 * methods become ChunkProjector.prototype methods via Object.assign().
 *
 * THREE.js and OrbitControls are still loaded as classic <script> tags so
 * they remain globally available as window.THREE; this file uses them via
 * that global, which is fine — ES modules can access window globals.
 *
 * Load order in index.html:
 *   1. three.min.js          (classic, sets window.THREE)
 *   2. OrbitControls.js      (classic, extends window.THREE)
 *   3. chunk_projector.js    (type="module" — this file)
 */

// NOTE: these static-import URLs intentionally do NOT carry a ?v=…
// cache-buster. Static imports are resolved before any user code can
// inject a version. To force a refresh of a cp/* module after editing
// it, bump the import URLs below (e.g. change ./cp/layout.js to
// ./cp/layout.js?v=20) — backend/main.py's _asset_version() bumps the
// top-level chunk_projector.js?v=<mtime> automatically, but ES module
// imports rely on URL equality for cache hits, so the inner URLs have
// to change separately. Adding a version param literal is the simplest
// way that survives the import resolver.
import { layOutNode, _hashUnit, _hslToRgb, DOC_RADIUS, INST_RADIUS, _layoutCache, fibSphereUnit, docShellRadius, clusterRadius } from './cp/layout.js?v=55';
import { IMAGE_EXTS, VIDEO_EXTS, AUDIO_EXTS, MediaMixin }           from './cp/media.js?v=55';
import { UiUtilsMixin }       from './cp/ui_utils.js?v=55';
import { EdgeManagerMixin }   from './cp/edge_manager.js?v=55';
import { InstanceManagerMixin } from './cp/instance_manager.js?v=55';
import { SpriteManagerMixin } from './cp/sprite_manager.js?v=55';
import { NodeLoaderMixin }    from './cp/node_loader.js?v=55';
import { BillboardMixin }     from './cp/billboard.js?v=55';
import { WorkspaceMixin }     from './cp/workspace.js?v=55';
import { InteractionMixin }   from './cp/interaction.js?v=55';
import { AnimationMixin }     from './cp/animation.js?v=55';
import { SearchMixin }        from './cp/search.js?v=55';
import { ScannerMixin }       from './cp/scanner.js?v=55';
import { ConceptGraphMixin }  from './cp/concept_graph.js?v=55';
import { ForceLayoutMixin }  from './cp/force_layout.js?v=55';
import { TelemetryMixin }    from './cp/telemetry.js?v=55';
// §6.1/§707/§709 — pure 6D-UMAP colour maths (no THREE/DOM; unit-tested by
// cp/hsv_color.test.mjs). Exposed as statics so mixin methods reach them via
// this.constructor.<fn> (same pattern as layout.js _hslToRgb / fibSphereUnit).
import { umap6ToHsl, azimuthToHuePhase, applyHuePhase, hslToRgb, umap6ToRgb255 } from './cp/hsv_color.js?v=55';

console.log('[ChunkProjector] Script loaded (modular)');

class ChunkProjector {
    // ── Static media extension sets (mirrored by MediaMixin) ─────────────────
    static IMAGE_EXTS = IMAGE_EXTS;
    static VIDEO_EXTS = VIDEO_EXTS;
    static AUDIO_EXTS = AUDIO_EXTS;

    // ── Static layout constants & pure functions ──────────────────────────────
    static DOC_RADIUS    = DOC_RADIUS;
    static INST_RADIUS   = INST_RADIUS;
    static _layoutCache  = _layoutCache;
    static _hashUnit     = _hashUnit;
    static _hslToRgb     = _hslToRgb;
    static layOutNode    = layOutNode;
    // Exposed for instance_manager's _relayoutSphericalGrowth, which
    // computes Fibonacci positions directly without going through
    // layOutNode (cleaner control flow + skip path for UMAP-locked
    // nodes).
    static fibSphereUnit  = fibSphereUnit;
    static docShellRadius = docShellRadius;
    static clusterRadius  = clusterRadius;

    // ── §6.1/§707/§709 pure 6D-UMAP colour maths (cp/hsv_color.js) ────────────
    static umap6ToHsl       = umap6ToHsl;
    static azimuthToHuePhase = azimuthToHuePhase;
    static applyHuePhase    = applyHuePhase;
    static hslToRgb         = hslToRgb;
    static umap6ToRgb255    = umap6ToRgb255;

    // ─────────────────────────────────────────────────────────────────────────
    constructor() {
        console.log('[ChunkProjector] Constructor');

        // THREE objects (scene built by AnimationMixin.initScene)
        this.scene    = null;
        this.camera   = null;
        this.renderer = null;
        this.controls = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse     = new THREE.Vector2();
        this.clock     = new THREE.Clock();
        this.animationTime = 0;

        // InstancedMesh pool (AnimationMixin.initScene → InstanceManagerMixin._createInstancedMeshes)
        this.docInstancedMesh  = null;
        this.instInstancedMesh = null;
        this.nodeInstanceMap   = new Map(); // id → { isDoc, index, originalColor }
        this._freeDocIndices   = [];
        this._freeInstIndices  = [];
        this._docInstanceIdToNode  = [];
        this._instInstanceIdToNode = [];

        // Data maps
        this.dataMap        = new Map(); // id → raw node
        this.initialNodeData = new Map(); // id → { position, umapColor }
        this.selectedId     = null;
        this.hoveredId      = null;
        this.searchResults  = null;
        this.lastSearchPayload = null;

        // Document collapse animation
        this.docCollapseTarget = new Map();
        this.docCollapseState  = new Map();

        // Per-chunk override of the doc-collapse state, used by the
        // search-panel "expanding spine" effect: scrolling a result row
        // into the viewport sets this chunk's target to 0 (pop out from
        // hub), scrolling it back out sets target to 1 (fold back into
        // hub). Both Maps mirror the doc-collapse Maps (target =
        // commanded, state = current animated). When an entry exists
        // here, it takes precedence over the chunk's parent doc state.
        this.chunkCollapseTarget = new Map();
        this.chunkCollapseState  = new Map();
        this.edges    = [];
        this.linesMesh = null;

        // Detail fetching
        this.detailsFetchQueue = new Set();

        // Per-scan streaming state (reset in triggerScan).
        // _pendingChunks: chunk_id → { url, chunk } — metadata from chunk_added
        //   that arrives before the matching chunk_instances_partial.
        // _chunkIdToInstances: chunk_id → Set<instance_id> — reverse map
        //   needed to remove/replace instances when chunk_removed fires.
        // _pendingIndexRows: rows waiting for instances_indexed before lazy fetch.
        this._pendingChunks      = new Map();
        this._chunkIdToInstances = new Map();
        this._pendingIndexRows   = [];

        // Sprites
        this._imageSprites       = new Map();
        this._extraSprites       = new Map();
        this._imageTextureCache  = new Map();
        this._imageProxyFailures = new Set();
        this._extraConnectorsMesh = null;

        // Pinned knowledge panels
        this._pinnedPanels   = new Map();
        this._panelHoverCount = 0;

        // File tree & workspaces
        this.workspaces       = this.loadWorkspaces();
        if (this.workspaces.length === 0) this.createWorkspace('Default Workspace');
        this.activeWorkspaceId = this.workspaces[0].id;
        this.domainTree        = new Map();
        this.expandedFolders   = new Set(['ft-domains', `ft-ws-${this.workspaces[0].id}`]);
        this.wsEditTimers      = new Map();
        this.wsEditOriginals   = new Map();

        // Drag detection
        this.isDragging   = false;
        this.mouseDownPos = { x: 0, y: 0 };

        // Background video
        this.backgroundMesh     = null;
        this.backgroundDistance = 500;

        // Snow-globe spatial rotation. (The old `colorVelocity` time-based
        // RGB-space colour tumble is removed: chunk colour is now the UMAP
        // content-HSV rotated by the camera-azimuth hue phase — see
        // animation.js animate() and cp/hsv_color.js, §6.1/§707.)
        this.spatialVelocity = { x: 0.05, y: 0.1,  z: 0.02 };

        // Init sequence
        this.initMaroniteTheme();
        this.initScene();       // replaces old init() — see AnimationMixin
        this.initLoadingBar();
        this.loadNodes();
        this.initSidebar();
        this.initSnapshot();
        this.initFileTree();
        this.initRainbowObserver();
        this.initBillboardArrow();
        this.initConceptGraph();   // 2D concept-graph editor overlay (hidden until user toggles)

        // Auto-detect scans started externally (e.g. scripts/scan.py in
        // backend-delegation mode) and attach to their live WS stream so
        // the GUI shows spheres without the user clicking Scan.
        // The call is intentionally fire-and-forget: any error is swallowed
        // inside checkForActiveScan and the UI state remains clean.
        setTimeout(() => this.checkForActiveScan(), 500);
    }
}

// ── Apply all mixins ─────────────────────────────────────────────────────────
// Order matters only when two mixins define the same key (last wins).
// The ordering below follows data-flow: lower-level helpers first.
Object.assign(ChunkProjector.prototype,
    UiUtilsMixin,           // theme, loading bar, log overlay, string utils
    EdgeManagerMixin,       // rebuildEdges, _rebuildEdgesSoon, _requestUIUpdate
    InstanceManagerMixin,   // _createInstancedMeshes … _addNodeInstance
    MediaMixin,             // extractMediaFromHtml, _classifyMediaUrl, renderBillboardMedia
    SpriteManagerMixin,     // _spawnImageBillboards, _lazyLoadAllNodeDetails
    NodeLoaderMixin,        // loadNodes, _buildSceneFromPayload, addNodesIncrementally
    BillboardMixin,         // showBillboard, hideBillboard, pinBillboard …
    WorkspaceMixin,         // initFileTree, renderFileTree, workspaces …
    InteractionMixin,       // getIntersects, onMouseMove, onClick, selectNode …
    AnimationMixin,         // initScene (replaces init()), animate(), initBackground …
    SearchMixin,            // initSidebar, triggerSearch, renderSearchResults …
    ScannerMixin,           // initSnapshot, triggerScan, setScanStatus
    ConceptGraphMixin,      // 2D concept-graph editor overlay (template-with-{vars})
    ForceLayoutMixin,       // UMAP + force-directed-along-root-rays layout (Mortegon §2)
    TelemetryMixin,         // MutationObserver → POST /api/ui/telemetry (CLI bridge)
);

// ── Bootstrap ────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    if (typeof THREE === 'undefined') {
        console.error('[ChunkProjector] THREE is not loaded');
        const box = document.createElement('div');
        box.style.cssText = 'position:fixed;top:20px;left:20px;background:#300;color:#fff;padding:20px;z-index:9999;';
        box.textContent   = 'THREE.js failed to load. Check network.';
        document.body.appendChild(box);
        return;
    }
    window.app = new ChunkProjector();
    // Wire MutationObservers that report DOM changes back to the
    // backend (drained by the CLI's ``ui-telemetry`` action). Fires
    // after a brief delay so the projector's initial DOM is in place.
    if (typeof window.app._telemetryInit === 'function') {
        try { window.app._telemetryInit(); }
        catch (e) { console.warn('[telemetry] init failed', e); }
    }
});
