// stepper.test.mjs — STEP-01 unit coverage for the pure advance-and-focus
// driver. No network, no THREE renderer: fetch/flyToNode/highlightNode are
// injected stubs (the dependency-injection split documented in
// 08-PATTERNS.md / the plan's Task 3 <action>).
import test from "node:test";
import assert from "node:assert/strict";

import { advanceAndFocus } from "./stepper.mjs";

function fakeFetchResolving(signalId, extra = {}) {
  const calls = [];
  const fetchFn = async (url, opts) => {
    calls.push({ url, opts });
    return {
      json: async () => ({
        ok: true,
        state: {
          signal_stream: {
            card1: { card_id: "card1", total: 3, signal_index: 1, signal_id: signalId, ...extra },
          },
        },
      }),
    };
  };
  fetchFn.calls = calls;
  return fetchFn;
}

test("Test 1: advanceAndFocus POSTs to /api/ui/signal_advance and, on a resolved signal_id, calls flyToNode + highlightNode exactly once each", async () => {
  const fetchFn = fakeFetchResolving("chunk_b");
  let flyCalls = 0, flyArg = null;
  let hiCalls = 0, hiArg = null;
  const flyToNode = (id) => { flyCalls += 1; flyArg = id; return true; };
  const highlightNode = (id) => { hiCalls += 1; hiArg = id; return true; };

  const result = await advanceAndFocus("card1", 1, { fetch: fetchFn, flyToNode, highlightNode });

  assert.strictEqual(fetchFn.calls.length, 1, "POSTs exactly once");
  assert.strictEqual(fetchFn.calls[0].url, "/api/ui/signal_advance");
  const body = JSON.parse(fetchFn.calls[0].opts.body);
  assert.strictEqual(body.card_id, "card1");
  assert.strictEqual(body.step, 1);

  assert.strictEqual(flyCalls, 1, "flyToNode called exactly once");
  assert.strictEqual(flyArg, "chunk_b");
  assert.strictEqual(hiCalls, 1, "highlightNode called exactly once");
  assert.strictEqual(hiArg, "chunk_b");

  assert.strictEqual(result.ok, true);
  assert.strictEqual(result.chunkId, "chunk_b");
});

test("Test 2: when the advance response carries no signal_id (null), advanceAndFocus calls neither flyToNode nor highlightNode", async () => {
  const fetchFn = fakeFetchResolving(null);
  let flyCalls = 0, hiCalls = 0;
  const flyToNode = () => { flyCalls += 1; return true; };
  const highlightNode = () => { hiCalls += 1; return true; };

  const result = await advanceAndFocus("card1", 1, { fetch: fetchFn, flyToNode, highlightNode });

  assert.strictEqual(flyCalls, 0, "flyToNode NOT called when signal_id is unresolved");
  assert.strictEqual(hiCalls, 0, "highlightNode NOT called when signal_id is unresolved");
  assert.strictEqual(result.chunkId, null);
  assert.strictEqual(result.ok, true, "the advance itself still reports ok even with no resolved focus target");
});

test("Test 3 (one-way invariant): advanceAndFocus wires no 3D->2D callback — the module imports nothing from projector.mjs and registers no event listeners", async () => {
  // Structural assertion #1: the module source never imports projector.mjs
  // (it receives flyToNode/highlightNode purely via injected deps — it has
  // no static binding to the projector at all, so it cannot also reach
  // into the projector's click/onFrame hooks to wire a callback).
  const fs = await import("node:fs");
  const src = fs.readFileSync(new URL("./stepper.mjs", import.meta.url), "utf8");
  assert.ok(!/from\s+["']\.\/projector\.mjs["']/.test(src), "stepper.mjs must not import projector.mjs directly");
  assert.ok(!/addEventListener/.test(src), "stepper.mjs must not register any event listener (no 3D->2D wiring)");

  // the only EXECUTABLE-CODE occurrence of the route path must be the
  // single outbound POST call (2D -> backend) — never inside a
  // callback/listener body that a 3D click could trigger. Strip comment
  // lines first so doc prose mentioning the route name doesn't inflate
  // the count.
  const codeOnly = src
    .split("\n")
    .filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line))
    .join("\n");
  const routeOccurrences = [...codeOnly.matchAll(/\/api\/ui\/signal_advance/g)];
  assert.strictEqual(routeOccurrences.length, 1, "the signal_advance route path appears exactly once in executable code: the outbound POST url");

  // Structural assertion #2 (behavioural): calling advanceAndFocus must
  // not register anything onto the injected flyToNode/highlightNode fns
  // themselves (e.g. no monkey-patching them into callbacks) — they are
  // called directly and synchronously within this single invocation, and
  // nothing about the call wires them to fire AGAIN on a later 3D event.
  const fetchFn = fakeFetchResolving("chunk_a");
  let calls = 0;
  const flyToNode = () => { calls += 1; return true; };
  const highlightNode = () => { calls += 1; return true; };
  await advanceAndFocus("card1", 1, { fetch: fetchFn, flyToNode, highlightNode });
  assert.strictEqual(calls, 2, "exactly one flyToNode + one highlightNode call for this single advance — no extra/deferred re-firing");
});
