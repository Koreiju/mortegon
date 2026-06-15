/**
 * tests/test_workspace.js — Tests for cp/workspace.js workspace management
 * logic (loadWorkspaces, saveWorkspaces, createWorkspace, addUrlToActiveWorkspace,
 * removeUrlFromWorkspace, toggleUrlVisibility, deleteWorkspace, etc.).
 *
 * Uses a minimal in-memory localStorage stub so these tests run anywhere.
 */

import { describe, it, assert, runAll } from './test_runner.js';
import { WorkspaceMixin } from '../cp/workspace.js';

// ── localStorage stub ────────────────────────────────────────────────────────
function makeLocalStorage() {
    const store = {};
    return {
        getItem:    (k)    => k in store ? store[k] : null,
        setItem:    (k, v) => { store[k] = String(v); },
        removeItem: (k)    => { delete store[k]; },
        clear:      ()     => { Object.keys(store).forEach(k => delete store[k]); },
        _store: store,
    };
}

// ── Context factory ──────────────────────────────────────────────────────────
function makeCtx(overrides = {}) {
    const ls = makeLocalStorage();
    const ctx = Object.assign(Object.create(WorkspaceMixin), {
        // Workspace state
        workspaces:       [],
        activeWorkspaceId: null,
        domainTree:       new Map(),
        expandedFolders:  new Set(),
        wsEditTimers:     new Map(),
        wsEditOriginals:  new Map(),
        // Stubs for methods called by workspace methods
        nodeInstanceMap:   new Map(),
        dataMap:           new Map(),
        initialNodeData:   new Map(),
        _imageSprites:     new Map(),
        lastSearchPayload: null,
        applyWorkspaceVisibility() {},
        renderFileTree()    {},
        renderUrlBuckets()  {},
        renderSearchResults() {},
        _setInstanceVisible() {},
        _setInstanceTransform() {},
        _freeInstance() {},
        rebuildEdges()  {},
        escape:          (s) => String(s ?? ''),
        shortenUrl:      (u) => u,
        // Override localStorage
        _ls: ls,
        ...overrides,
    });
    // Redirect loadWorkspaces / saveWorkspaces to use the stub store.
    ctx.loadWorkspaces = function() {
        try { const raw = ls.getItem('wfh_workspaces'); if (raw) return JSON.parse(raw); }
        catch (e) { }
        return [];
    };
    ctx.saveWorkspaces = function() {
        ls.setItem('wfh_workspaces', JSON.stringify(this.workspaces));
    };
    return ctx;
}

// ── createWorkspace ──────────────────────────────────────────────────────────
describe('createWorkspace', () => {
    it('adds a workspace to this.workspaces', () => {
        const ctx = makeCtx();
        ctx.createWorkspace('Test WS');
        assert.equal(ctx.workspaces.length, 1);
        assert.equal(ctx.workspaces[0].name, 'Test WS');
    });

    it('returns the new workspace id', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('My WS');
        assert.ok(typeof id === 'string' && id.startsWith('ws_'));
    });

    it('initialises urls and hiddenUrls to empty arrays', () => {
        const ctx = makeCtx();
        ctx.createWorkspace('Empty');
        const ws = ctx.workspaces[0];
        assert.deepEqual(ws.urls, []);
        assert.deepEqual(ws.hiddenUrls, []);
    });

    it('persists to localStorage via saveWorkspaces', () => {
        const ctx = makeCtx();
        ctx.createWorkspace('Persisted');
        const saved = JSON.parse(ctx._ls.getItem('wfh_workspaces'));
        assert.equal(saved.length, 1);
        assert.equal(saved[0].name, 'Persisted');
    });
});

// ── loadWorkspaces ───────────────────────────────────────────────────────────
describe('loadWorkspaces', () => {
    it('returns [] when localStorage is empty', () => {
        const ctx = makeCtx();
        assert.deepEqual(ctx.loadWorkspaces(), []);
    });

    it('deserialises previously saved workspaces', () => {
        const ctx = makeCtx();
        ctx.createWorkspace('Alpha');
        ctx.createWorkspace('Beta');
        const loaded = ctx.loadWorkspaces();
        assert.equal(loaded.length, 2);
        assert.equal(loaded[0].name, 'Alpha');
        assert.equal(loaded[1].name, 'Beta');
    });

    it('returns [] on malformed JSON', () => {
        const ctx = makeCtx();
        ctx._ls.setItem('wfh_workspaces', 'NOT_JSON');
        assert.deepEqual(ctx.loadWorkspaces(), []);
    });
});

// ── addUrlToActiveWorkspace ──────────────────────────────────────────────────
describe('addUrlToActiveWorkspace', () => {
    it('adds url to the active workspace', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('W1');
        ctx.activeWorkspaceId = id;
        ctx.addUrlToActiveWorkspace('https://example.com');
        const ws = ctx.workspaces.find(w => w.id === id);
        assert.ok(ws.urls.includes('https://example.com'));
    });

    it('does not add the same url twice', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('W2');
        ctx.activeWorkspaceId = id;
        ctx.addUrlToActiveWorkspace('https://x.com');
        ctx.addUrlToActiveWorkspace('https://x.com');
        const ws = ctx.workspaces.find(w => w.id === id);
        assert.equal(ws.urls.length, 1);
    });
});

// ── removeUrlFromWorkspace ───────────────────────────────────────────────────
describe('removeUrlFromWorkspace', () => {
    it('removes a url from the workspace', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('W3');
        ctx.activeWorkspaceId = id;
        const ws = ctx.workspaces.find(w => w.id === id);
        ws.urls.push('https://a.com', 'https://b.com');
        ctx.removeUrlFromWorkspace(id, 'https://a.com');
        assert.ok(!ws.urls.includes('https://a.com'));
        assert.ok(ws.urls.includes('https://b.com'));
    });

    it('also removes from hiddenUrls', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('W4');
        const ws  = ctx.workspaces.find(w => w.id === id);
        ws.urls.push('https://c.com');
        ws.hiddenUrls.push('https://c.com');
        ctx.removeUrlFromWorkspace(id, 'https://c.com');
        assert.ok(!ws.hiddenUrls.includes('https://c.com'));
    });
});

// ── toggleUrlVisibility ──────────────────────────────────────────────────────
describe('toggleUrlVisibility', () => {
    it('hides a visible url', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('W5');
        ctx.activeWorkspaceId = id;
        const ws  = ctx.workspaces.find(w => w.id === id);
        ws.urls.push('https://d.com');
        ctx.toggleUrlVisibility(id, 'https://d.com');
        assert.ok(ws.hiddenUrls.includes('https://d.com'));
    });

    it('shows a hidden url', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('W6');
        ctx.activeWorkspaceId = id;
        const ws  = ctx.workspaces.find(w => w.id === id);
        ws.urls.push('https://e.com');
        ws.hiddenUrls.push('https://e.com');
        ctx.toggleUrlVisibility(id, 'https://e.com');
        assert.ok(!ws.hiddenUrls.includes('https://e.com'));
    });

    it('initialises hiddenUrls if undefined', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('W7');
        ctx.activeWorkspaceId = id;
        const ws  = ctx.workspaces.find(w => w.id === id);
        delete ws.hiddenUrls;
        ws.urls.push('https://f.com');
        ctx.toggleUrlVisibility(id, 'https://f.com');
        assert.ok(Array.isArray(ws.hiddenUrls));
    });
});

// ── deleteWorkspace ──────────────────────────────────────────────────────────
describe('deleteWorkspace', () => {
    it('removes the workspace from the array', () => {
        const ctx  = makeCtx();
        const id1  = ctx.createWorkspace('Keep');
        const id2  = ctx.createWorkspace('Delete');
        ctx.activeWorkspaceId = id1;
        // deleteWorkspace calls confirm() — stub it
        const origConfirm = globalThis.confirm;
        globalThis.confirm = () => true;
        ctx.deleteWorkspace(id2, null);
        globalThis.confirm = origConfirm;
        assert.ok(!ctx.workspaces.find(w => w.id === id2), 'Workspace not deleted');
        assert.equal(ctx.workspaces.length, 1);
    });

    it('refuses to delete the last workspace', () => {
        const ctx = makeCtx();
        const id  = ctx.createWorkspace('Only');
        ctx.activeWorkspaceId = id;
        ctx.deleteWorkspace(id, null); // should silently return
        assert.equal(ctx.workspaces.length, 1);
    });

    it('switches active to first remaining workspace when active is deleted', () => {
        const ctx  = makeCtx();
        const id1  = ctx.createWorkspace('W1');
        const id2  = ctx.createWorkspace('W2');
        ctx.activeWorkspaceId = id2;
        const origConfirm = globalThis.confirm;
        globalThis.confirm = () => true;
        ctx.deleteWorkspace(id2, null);
        globalThis.confirm = origConfirm;
        assert.equal(ctx.activeWorkspaceId, id1);
    });
});

runAll();
