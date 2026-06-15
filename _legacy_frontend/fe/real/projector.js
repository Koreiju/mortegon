/**
 * fe/real/projector.js — the Real register: the 3D canvas.
 *
 * Renders the backend's canonical 6-vectors (x,y,z,h,s,v) as HSV spheres.
 * Computes NO layout — it only renders + tweens toward the coords the
 * LayoutService sends. 3D nodes are the only saturated pixels in the UI
 * (the theme exception). Driven by the one rAF loop (pulse/raf.js).
 * (code_specs/frontend/real.md)
 */

import { Reconciler } from '../pulse/reconciler.js';

const SPHERE_R = 0.45;

export class Projector {
  constructor(store, { canvas, tweens, onHover, onPick } = {}) {
    this.store = store;
    this.tweens = tweens;
    this.onHover = onHover || (() => {});
    this.onPick = onPick || (() => {});
    this.canvas = canvas;
    this.meshes = new Map();          // id -> THREE.Mesh
    this._geo = new THREE.SphereGeometry(SPHERE_R, 16, 12);
    this._ray = new THREE.Raycaster();
    this._pointer = new THREE.Vector2();
    this._hoverId = null;
    this._initThree();
    this._bindPointer();
  }

  _initThree() {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);           // black core (theme)
    this.camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 4000);
    this.camera.position.set(0, 0, 80);
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h, false);
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const dir = new THREE.DirectionalLight(0xffffff, 0.5); dir.position.set(1, 1, 1); this.scene.add(dir);
    if (THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true; this.controls.dampingFactor = 0.08;
    }
    window.addEventListener('resize', () => this._resize());
  }

  _resize() {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
  }

  _bindPointer() {
    const el = this.renderer.domElement;
    el.addEventListener('pointermove', (e) => {
      const r = el.getBoundingClientRect();
      this._pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
      this._pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
      this._pendingHover = { x: e.clientX, y: e.clientY };
    });
    el.addEventListener('click', () => { if (this._hoverId != null) this.onPick(this._hoverId, this._screenOf(this._hoverId)); });
  }

  /** One rAF tick: reconcile meshes to coords, tween, raycast hover, render. */
  tick() {
    const coords = this.store.read('layoutCoords');
    const prov = this.store.read('provenance');
    const hiddenUrls = this.store.read('ui')?.hidden_urls || [];

    Reconciler.apply(this.meshes, coords, {
      onEnter: (id) => this._addMesh(id, coords.get(id)),
      onUpdate: (id, vec, mesh) => this._updateMesh(mesh, vec),
      onExit: (id, mesh) => { this.scene.remove(mesh); mesh.material.dispose?.(); },
    });

    // hover raycast (throttled to once per frame via _pendingHover)
    if (this._pendingHover) {
      this._ray.setFromCamera(this._pointer, this.camera);
      const hit = this._ray.intersectObjects([...this.meshes.values()], false)[0];
      const id = hit ? hit.object.userData.id : null;
      if (id !== this._hoverId) { this._hoverId = id; this.onHover(id, this._pendingHover); }
      this._pendingHover = null;
    }

    this.controls?.update();
    this.renderer.render(this.scene, this.camera);
  }

  _addMesh(id, vec) {
    const mat = new THREE.MeshLambertMaterial({ color: this._hsv(vec) });
    const mesh = new THREE.Mesh(this._geo, mat);
    mesh.userData.id = id;
    const p = (vec && vec.length >= 3) ? [vec[0], vec[1], vec[2]] : [0, 0, 0];
    mesh.position.set(p[0], p[1], p[2]);
    this.scene.add(mesh);
    this.meshes.set(id, mesh);
    return mesh;
  }

  _updateMesh(mesh, vec) {
    if (!mesh || !vec) return;
    this.tweens.toVec3(mesh, [vec[0], vec[1], vec[2]], { ms: 600 });   // retarget from current
    mesh.material.color.copy(this._hsv(vec));
  }

  _hsv(vec) {
    const c = new THREE.Color();
    if (vec && vec.length >= 6) c.setHSL(((vec[3] % 1) + 1) % 1, clamp01(vec[4]), clamp01(vec[5]));
    else c.setHSL(0.58, 0.5, 0.6);
    return c;
  }

  _screenOf(id) {
    const m = this.meshes.get(id); if (!m) return null;
    const v = m.position.clone().project(this.camera);
    const r = this.renderer.domElement.getBoundingClientRect();
    return { x: (v.x * 0.5 + 0.5) * r.width + r.left, y: (-v.y * 0.5 + 0.5) * r.height + r.top };
  }

  /** Project a stored id to screen px (for the 2D↔3D connector). */
  project(id) { return this._screenOf(id); }

  /** Frame the whole cloud (called after a layout refit or on demand). */
  frameAll() {
    const pts = [...this.meshes.values()].map((m) => m.position);
    if (!pts.length) return;
    const box = new THREE.Box3().setFromPoints(pts);
    const c = box.getCenter(new THREE.Vector3());
    const r = Math.max(box.getSize(new THREE.Vector3()).length() * 0.6, 10);
    this.controls && this.controls.target.copy(c);
    this.camera.position.set(c.x, c.y, c.z + r * 1.8);
  }
}

function clamp01(x) { return Math.max(0, Math.min(1, x)); }
