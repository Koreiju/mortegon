// Phase 3 — Apparition halo render (§7 / §15.2 / HALO-01/02).
//
// The halo's MODEL (constant-similarity ray, along-line slide, z-above-slate,
// scroll re-anchor, name-only phantoms) is unit-covered by
// `backend/static/js/fe/magic_markdown_halo.test.mjs` (5/5), and the §15.1
// circular collapsed-node form is exercised in `edit.spec.js`. These are the
// LIVE-editor browser acceptance specs — they need a rendered focal field with a
// halo open (a fixture scan + a click on a collapsed node), so they are the
// build/verify targets for HALO-01/02 (un-fixme as Phase 3's live halo lands).
const { test } = require("@playwright/test");

test.fixme("HALO-01 clicking a collapsed node fires a halo of NAME-only phantoms", async () => {
  // open the served `/` editor on a scanned workspace, click a collapsed circular
  // node → expect halo phantoms each showing only the candidate name (no score chips).
});

test.fixme("HALO-02 phantoms paint ABOVE the slate (z-order) and re-anchor to the focal token", async () => {
  // assert the halo overlay z-index > the focal card's; then scroll the slate /
  // drag the card and assert the phantoms track the focal-token rect (not the
  // static card rect) — the two independent §T.4 fixes.
});

test.fixme("HALO-02 constant-similarity ray + along-line slide as the 3D camera orbits", async () => {
  // orbit the projector camera (azimuth) → phantoms slide along their rays,
  // preserving the constant triple-product similarity mapping (§15.2 / O.18).
});
