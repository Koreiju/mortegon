/**
 * §R.5 — node-level tests for the frontend markdown-gesture outline parser
 * (`_looksLikeMarkdownTree` / `_parseMarkdownTopLevel` on ConceptGraphMixin).
 *
 * Pure-function surface: no DOM needed. Asserts the frontend strategy agrees
 * with the backend `parse_markdown_tree`/`decompose_top_level` semantics
 * (compile_pipeline.py) — the §R.1 commutation anchor.
 *
 * Run: node backend/static/js/tests/test_markdown_parse.mjs
 */

import { ConceptGraphMixin as M } from '../cp/concept_graph.js';

let passed = 0, failed = 0;
function check(name, cond, detail = '') {
    if (cond) { passed += 1; console.log(`  ✓ ${name}`); }
    else { failed += 1; console.error(`  ✗ ${name} ${detail}`); }
}

console.log('▶ _looksLikeMarkdownTree gesture gate');
check('dash gesture', M._looksLikeMarkdownTree('- alpha\n- beta'));
check('numbered gesture', M._looksLikeMarkdownTree('1. first\n2. second'));
check('paren-numbered gesture', M._looksLikeMarkdownTree('1) first\n2) second'));
check('tab gesture without bullets', M._looksLikeMarkdownTree('opener\n\tnested'));
check('rejects single prose line', !M._looksLikeMarkdownTree('just a sentence'));
check('rejects flat multi-line prose', !M._looksLikeMarkdownTree('line one\nline two'));
check('rejects empty', !M._looksLikeMarkdownTree(''));

console.log('▶ _parseMarkdownTopLevel entries');
{
    const e = M._parseMarkdownTopLevel('- alpha: 1\n- beta: two');
    check('dash kv keys', e && e.length === 2 && e[0].key === 'alpha' && e[1].key === 'beta',
          JSON.stringify(e));
    check('dash kv values', e && e[0].value === '1' && e[1].value === 'two');
}
{
    const e = M._parseMarkdownTopLevel('- parent:\n\t- child_a: 1\n\t- child_b: 2\n- flat: 3');
    check('nested block under parent', e && e.length === 2 && e[0].key === 'parent',
          JSON.stringify(e));
    check('child block keeps markdown (recursable)',
          e && e[0].value.includes('- child_a: 1') && e[0].value.includes('- child_b: 2'));
    check('flat sibling intact', e && e[1].key === 'flat' && e[1].value === '3');
}
{
    const e = M._parseMarkdownTopLevel('1. first step\n\t- detail: a\n2. second step');
    check('numbered labelled branch uses label key',
          e && e[0].key === 'first step' && e[0].value.includes('- detail: a'),
          JSON.stringify(e));
    check('numbered leaf uses positional key', e && e[1].key === '1' && e[1].value === 'second step');
}
{
    const e = M._parseMarkdownTopLevel('- alpha: 1\nbare sibling\n- beta: 2');
    check('newline-with-trailing-text is a sibling', e && e.length === 3, JSON.stringify(e));
    check('bare line keeps its text', e && e.some(x => x.value === 'bare sibling'));
}
{
    const e = M._parseMarkdownTopLevel('- a: 1\n\n\n- b: 2');
    check('blank newlines are non-structural', e && e.length === 2, JSON.stringify(e));
}
{
    const e = M._parseMarkdownTopLevel('- key: inline\n\t- sub: x');
    check('inline value + children both kept',
          e && e[0].value.startsWith('inline') && e[0].value.includes('- sub: x'),
          JSON.stringify(e));
}
{
    check('prose returns null', M._parseMarkdownTopLevel('plain prose only') === null);
}
{
    // Space-indent nesting (2-space)
    const e = M._parseMarkdownTopLevel('- parent:\n  - child: 1');
    check('space-indent nests', e && e.length === 1 && e[0].value.includes('- child: 1'),
          JSON.stringify(e));
}

console.log('▶ _parseBracketedTopLevel (§E.1 bracketed lists)');
{
    const e = M._parseBracketedTopLevel('[alpha, beta, gamma]');
    check('bracketed simple', JSON.stringify(e) === '["alpha","beta","gamma"]', JSON.stringify(e));
}
{
    const e = M._parseBracketedTopLevel('(a, b, c)');
    check('parens form', JSON.stringify(e) === '["a","b","c"]', JSON.stringify(e));
}
{
    const e = M._parseBracketedTopLevel('[a, [b, c], d]');
    check('nested kept as item', e && e.length === 3 && e[1] === '[b, c]', JSON.stringify(e));
}
{
    const e = M._parseBracketedTopLevel('["x, y", z]');
    check('quoted comma guarded', e && e[0] === 'x, y' && e[1] === 'z', JSON.stringify(e));
}
{
    check('strict JSON rejected (JSON strategy owns it)',
          M._parseBracketedTopLevel('["a", "b"]') === null);
    check('plain text rejected', M._parseBracketedTopLevel('plain') === null);
    check('unclosed rejected', M._parseBracketedTopLevel('[unclosed') === null);
}
{
    // HTML strategy gate is browser-only (DOMParser): under Node it must
    // cleanly refuse rather than throw.
    check('_looksLikeHtmlTree refuses under Node (no DOMParser)',
          M._looksLikeHtmlTree('<article><h2>T</h2></article>') === false);
}

console.log(`\n${passed + failed} checks: ${passed} passed, ${failed} failed`);
process.exit(failed === 0 ? 0 : 1);
