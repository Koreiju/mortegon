/**
 * tests/three_stub.js — Minimal THREE.js stubs for Node-compatible testing.
 *
 * Import this file and assign to globalThis.THREE BEFORE calling any mixin
 * methods that reference THREE.  Because mixin methods reference THREE at
 * call-time (not at module-evaluation time), setting the global in the
 * module body is sufficient:
 *
 *   import * as THREE from './three_stub.js';
 *   globalThis.THREE = THREE;
 *   import { SomeMixin } from '../cp/some_module.js';
 *   // ... then create context and call methods — THREE is available.
 *
 * Only the subset used by the testable code paths is implemented.
 * Rendering-only operations (projectionMatrix, frustum, etc.) are no-ops.
 */

export const DynamicDrawUsage = 35048;

// ── Math utilities ────────────────────────────────────────────────────────────
export const MathUtils = {
    degToRad: (d) => d * Math.PI / 180,
};
// r128 alias
export const Math_ = MathUtils;

// ── Vector3 ───────────────────────────────────────────────────────────────────
export class Vector3 {
    constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
    clone()           { return new Vector3(this.x, this.y, this.z); }
    copy(v)           { this.x = v.x; this.y = v.y; this.z = v.z; return this; }
    set(x, y, z)      { this.x = x; this.y = y; this.z = z; return this; }
    applyMatrix4()    { return this; }          // stub — no transform
    lerp(v, t)        { this.x += (v.x - this.x) * t; this.y += (v.y - this.y) * t; this.z += (v.z - this.z) * t; return this; }
    subScalar(s)      { this.x -= s; this.y -= s; this.z -= s; return this; }
    addScalar(s)      { this.x += s; this.y += s; this.z += s; return this; }
    multiplyScalar(s) { this.x *= s; this.y *= s; this.z *= s; return this; }
}

// ── Color ─────────────────────────────────────────────────────────────────────
export class Color {
    constructor(r = 1, g = 1, b = 1) { this.r = r; this.g = g; this.b = b; }
    clone()           { return new Color(this.r, this.g, this.b); }
    copy(c)           { this.r = c.r; this.g = c.g; this.b = c.b; return this; }
    lerp(c, t)        { this.r += (c.r - this.r) * t; this.g += (c.g - this.g) * t; this.b += (c.b - this.b) * t; return this; }
    multiplyScalar(s) { this.r *= s; this.g *= s; this.b *= s; return this; }
    getHexString() {
        const h = (n) => Math.max(0, Math.min(255, Math.round(n * 255))).toString(16).padStart(2, '0');
        return h(this.r) + h(this.g) + h(this.b);
    }
}

// ── Matrix4 ───────────────────────────────────────────────────────────────────
export class Matrix4 {
    constructor() {
        this.elements = new Float32Array(16);
        // Identity
        this.elements[0] = this.elements[5] = this.elements[10] = this.elements[15] = 1;
    }
    makeScale(x, y, z) {
        const e = this.elements;
        e[0] = x; e[5] = y; e[10] = z; e[15] = 1;
        e[1]=e[2]=e[3]=e[4]=e[6]=e[7]=e[8]=e[9]=e[11]=e[12]=e[13]=e[14]=0;
        return this;
    }
    setPosition(v) {
        if (v && typeof v === 'object') {
            this.elements[12] = v.x || 0;
            this.elements[13] = v.y || 0;
            this.elements[14] = v.z || 0;
        }
        return this;
    }
    compose(pos, quat, scale) {
        const e = this.elements;
        // Write scale into diagonal
        if (scale) { e[0] = scale.x ?? 1; e[5] = scale.y ?? 1; e[10] = scale.z ?? 1; }
        // Write translation
        if (pos)   { e[12] = pos.x ?? 0;  e[13] = pos.y ?? 0;  e[14] = pos.z ?? 0; }
        return this;
    }
    decompose(pos, quat, scale) {
        const e = this.elements;
        if (pos)   { pos.x   = e[12]; pos.y   = e[13]; pos.z   = e[14]; }
        if (scale) { scale.x = e[0];  scale.y = e[5];  scale.z = e[10]; }
        return this;
    }
    makeRotationFromEuler() { return this; }
    multiplyMatrices()      { return this; }
}

// ── Quaternion ────────────────────────────────────────────────────────────────
export class Quaternion { constructor() {} }

// ── Euler ─────────────────────────────────────────────────────────────────────
export class Euler { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; } }

// ── InstancedMesh ─────────────────────────────────────────────────────────────
// Stores matrices and colours in in-memory arrays.  The key methods used by
// instance_manager.js are faithfully implemented so integration tests can
// verify that transforms and colours propagate correctly.
export class InstancedMesh {
    constructor(geometry, material, capacity) {
        this.geometry  = geometry;
        this.material  = material;
        this.count     = 0;
        this._cap      = capacity;
        this._matrices = Array.from({ length: capacity }, () => new Matrix4());
        this._colors   = Array.from({ length: capacity }, () => new Color());
        this.instanceMatrix = { needsUpdate: false, setUsage: () => {} };
        this.instanceColor  = { needsUpdate: false };
    }
    setMatrixAt(i, mat) { if (i < this._cap) this._matrices[i] = mat; }
    getMatrixAt(i, out)  {
        if (i < this._cap && out) {
            out.elements.set(this._matrices[i].elements);
        }
    }
    setColorAt(i, col) { if (i < this._cap) this._colors[i].copy(col); }
    getColorAt(i, out)  { if (i < this._cap && out) out.copy(this._colors[i]); }
    dispose() {}
}

// ── Scene ─────────────────────────────────────────────────────────────────────
export class Scene {
    constructor() { this.fog = null; this._objects = []; }
    add(obj)    { this._objects.push(obj); }
    remove(obj) { const i = this._objects.indexOf(obj); if (i !== -1) this._objects.splice(i, 1); }
}

// ── Geometry stubs ────────────────────────────────────────────────────────────
export class SphereGeometry { constructor() {} dispose() {} }
export class PlaneGeometry  { constructor() {} dispose() {} }

export class BufferGeometry {
    constructor() { this.attributes = {}; }
    setFromPoints() { return this; }
    setAttribute(name, attr) { this.attributes[name] = attr; }
    getAttribute(name)       { return this.attributes[name] || null; }
    dispose() {}
}

export class BufferAttribute {
    constructor(array, itemSize) {
        this.array    = array;
        this.itemSize = itemSize;
        this.needsUpdate = false;
    }
}

// ── Material stubs ────────────────────────────────────────────────────────────
export class MeshPhongMaterial  { constructor() {} dispose() {} }
export class MeshBasicMaterial  { constructor() {} dispose() {} }
export class LineBasicMaterial  { constructor() {} dispose() {} }
export class SpriteMaterial     { constructor(o) { this.map = o && o.map; } dispose() {} }

// ── Mesh / Sprite / LineSegments stubs ───────────────────────────────────────
export class Mesh {
    constructor(g, m) {
        this.geometry    = g;
        this.material    = m;
        this.position    = new Vector3();
        this.scale       = new Vector3(1, 1, 1);
        this.renderOrder = 0;
    }
    add() {}
}

export class Sprite {
    constructor(material) {
        this.material = material;
        this.position = new Vector3();
        this.scale    = new Vector3(1, 1, 1);
        this.visible  = true;
        this.userData = {};
    }
}

export class LineSegments {
    constructor(geometry, material) {
        this.geometry = geometry;
        this.material = material;
        this.visible  = true;
    }
    dispose() {}
}

// ── Other stubs ───────────────────────────────────────────────────────────────
export class FogExp2    { constructor() {} }
export class Raycaster  { setFromCamera() {} intersectObjects() { return []; } }
export class Vector2    { constructor(x = 0, y = 0) { this.x = x; this.y = y; } }
export class Clock      { getDelta() { return 0.016; } }
export class Frustum    { setFromProjectionMatrix() {} containsPoint() { return true; } }
export class Box3       {
    expandByPoint() {}
    isEmpty()       { return true; }
    getCenter(v)    { return v || new Vector3(); }
    getSize(v)      { return v || new Vector3(); }
}
export class TextureLoader { crossOrigin = ''; load() {} }
export class VideoTexture  { constructor() { this.minFilter = this.magFilter = 0; } }
export class PerspectiveCamera {
    constructor() {
        this.fov    = 60;
        this.aspect = 1;
        this.position = new Vector3();
        this.projectionMatrix = new Matrix4();
        this.matrixWorldInverse = new Matrix4();
    }
    updateProjectionMatrix() {}
    add() {}
}
export class WebGLRenderer {
    constructor() { this.domElement = { getBoundingClientRect: () => ({ left:0, top:0, width:800, height:600 }) }; }
    setSize()      {}
    setPixelRatio() {}
    render()       {}
}
export class AmbientLight     { constructor() {} }
export class DirectionalLight { constructor() { this.position = new Vector3(); } }
export class OrbitControls    { constructor() {} update() {} enableDamping = true; dampingFactor = 0.05; target = new Vector3(); }
