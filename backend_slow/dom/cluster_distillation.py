#!/usr/bin/env python3
"""
cluster_distillation.py — DEPRECATED — Distill web pages into chunk-wise instance HTML.

.. deprecated::
    The frequency-based distiller has been superseded by the content-tagged
    Patricia trie + ChunkBuilder pipeline (backend/dom/pipeline.py). That
    path produces pattern-keyed chunks with content_fields (knowledge panels)
    directly from the ContentTagger + XPathTreeBuilder, which is both faster
    and more semantically accurate than the v16 vocabulary-scorer heuristic.

    Prefer ``from backend.dom.pipeline import run_pipeline`` for any new
    entry point. This module is retained only so the legacy
    ``distilled_*`` CLI continues to work for ad-hoc inspection.

Usage:
    python cluster_distillation.py <html_file>

Output (in ./distilled_<basename>/):
    distilled.html        All chunks with deduped instance HTML
    chunk_NNN.html        Individual chunk files
    search.html           Search input instances (if present)
    pagination.html       Pagination/button instances (if present)

Instances are rendered using the v16 semantic deduplication mask,
which removes duplicate sibling subtrees (responsive rendering
copies) from each card. This produces clean per-instance HTML
with deduplicated titles, images, descriptions, and links.
"""

import re
import sys
from pathlib import Path

from .web_distiller_freq import (
    WebDistiller,
    ContentCoagulator,
    _VocabularyScorer,
    SearchInputCollector,
    PaginationCollector,
)


_CSS = """\
  .instance { border: 1px solid #ccc; margin: 8px; padding: 8px; }
  .instance-header { font-size: 0.8em; color: #666; margin-bottom: 4px; }
  .instance-meta { font-size: 0.75em; color: #888; margin-top: 4px; }
  .cist-tag { color: #d84315; font-weight: bold; }
"""


def _render_instance(dom, xpath, max_html=4000):
    """Render a single instance with dedup mask applied.

    Uses ContentCoagulator's static dedup methods to:
      1. Build a semantic mask identifying duplicate sibling subtrees
      2. Render HTML skipping masked subtrees + duplicate headings/media
      3. Extract text with three-layer deduplication
    """
    node = dom.xpath_one(xpath)
    if not node:
        return None, '', ''

    mask = ContentCoagulator._build_dedup_mask(node)
    html = ContentCoagulator._render_deduped_html(
        node, max_length=max_html, mask=mask
    )
    text = ContentCoagulator._dedup_text(
        node, max_length=500, mask=mask
    )
    return node, html, text


# ══════════════════════════════════════════════════════════════════
# Molecule splitting — 1D DP Sequence Segmentation (Phase 2)
# ══════════════════════════════════════════════════════════════════
#
# Replaces the legacy heuristic tag-counting BFS with a formal
# Dynamic Programming algorithm that evaluates ALL possible
# contiguous partitions and selects the mathematically optimal
# atom boundaries via a quality cost function + MDL stopping.
#
# Algorithm:
#   1. Extract tag-agnostic feature vectors per child node
#   2. Build prefix-sum arrays for O(1) range queries
#   3. Fill DP table: OPT[j] = max_i (OPT[i-1] + Q(i,j))
#   4. Backtrack to recover optimal split points
#   5. MDL criterion: only accept if split compresses description
#
# Complexity: O(C²) where C = direct children count.

import math

_HEADING_TAGS = frozenset({'h1', 'h2', 'h3', 'h4', 'h5', 'h6'})
_MEDIA_TAGS_DP = frozenset({'img', 'picture', 'video', 'source'})

# ── Quality function weights ─────────────────────────────────────
# α₁: navigable link = primary content signal
# α₂: heading = section boundary anchor
# α₃: media = visual content enrichment
# α₄: text mass = information density (sigmoid-smoothed)
# α₅: length penalty = prefer compact atoms over wide ones
_ALPHA_LINK = 3.0
_ALPHA_HEADING = 2.0
_ALPHA_MEDIA = 1.5
_ALPHA_TEXT = 1.0
_ALPHA_LENGTH = 0.5

# Per-atom MDL penalty: each additional atom in the partition must
# justify its existence by contributing quality exceeding this cost.
# This replaces the flat log₂(k) MDL penalty with a per-atom penalty
# baked directly into the DP recurrence, naturally penalizing
# over-segmentation while rewarding meaningful splits.
_PER_ATOM_PENALTY = 0.5


def _dp_sigmoid(x):
    """Smooth activation, clamped for numerical stability."""
    if x < -20.0:
        return 0.0
    if x > 20.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def _extract_child_features(node):
    """Extract a tag-agnostic structural feature vector from a subtree.

    Measures SEMANTIC DENSITY: text mass, navigable links, visual media,
    section headings, and substantial buttons. These are the universal
    signals that define whether a contiguous slice of siblings constitutes
    a meaningful content atom.

    Returns dict with: text_len, link_count, media_count, heading, button,
                       has_content
    """
    text_len = 0
    link_count = 0
    media_count = 0
    heading = 0
    button = 0

    for desc in node.iter_all():
        tag = getattr(desc, 'tag', '').lower()
        if tag.startswith('#'):
            continue

        # Text mass (tag-agnostic)
        text = (getattr(desc, 'text', '') or '').strip()
        tail = (getattr(desc, 'tail', '') or '').strip()
        text_len += len(text) + len(tail)

        # Navigable links: <a> with href and meaningful content
        if tag == 'a':
            href = desc.get_attr('href', '') if hasattr(desc, 'get_attr') else ''
            link_text = desc.get_text().strip() if hasattr(desc, 'get_text') else text
            aria = (desc.get_attr('aria-label', '') or '') if hasattr(desc, 'get_attr') else ''
            if href and (len(link_text) >= 3 or len(aria) >= 2):
                link_count += 1

        # Visual media
        if tag in _MEDIA_TAGS_DP:
            media_count += 1

        # Section headings
        if tag in _HEADING_TAGS:
            h_text = desc.get_text().strip() if hasattr(desc, 'get_text') else text
            if len(h_text) >= 5:
                heading = 1

        # Substantial buttons (FAQ/accordion pattern)
        if tag == 'button':
            btn_text = desc.get_text().strip() if hasattr(desc, 'get_text') else text
            if len(btn_text) >= 20:
                button = 1

    has_content = 1 if (text_len > 10 or link_count > 0 or media_count > 0) else 0

    return {
        'text_len': text_len,
        'link_count': link_count,
        'media_count': media_count,
        'heading': heading,
        'button': button,
        'has_content': has_content,
    }


def _atom_quality(i, j, k, pfx_link, pfx_heading, pfx_media,
                  pfx_text, pfx_content):
    """Evaluate quality of candidate atom children[i..j] (inclusive).

    Uses prefix-sum arrays for O(1) range queries.

    Rewards atoms with independent semantic identity (own link, heading,
    or media). Penalizes overly wide atoms. Returns -inf for empty atoms.

    **Navigability dampening:** An atom that has content but lacks any
    navigable signal (link or media) is not independently meaningful —
    it's structural text (like a title) that only makes sense attached
    to adjacent navigable content. Such atoms have their quality
    dampened by 0.1×, causing the DP to naturally:
      - Keep title+subtitle heading pairs together (neither has links)
      - Pair FAQ buttons with their adjacent answer panels
      - Group decorative wrappers with their content siblings
    """
    sum_link = pfx_link[j + 1] - pfx_link[i]
    sum_heading = pfx_heading[j + 1] - pfx_heading[i]
    sum_media = pfx_media[j + 1] - pfx_media[i]
    sum_text = pfx_text[j + 1] - pfx_text[i]
    sum_content = pfx_content[j + 1] - pfx_content[i]

    # Forbidden: atom containing zero content-bearing children
    if sum_content == 0:
        return float('-inf')

    q = 0.0
    q += _ALPHA_LINK * min(1, sum_link)
    q += _ALPHA_HEADING * min(1, sum_heading)
    q += _ALPHA_MEDIA * min(1, sum_media)
    q += _ALPHA_TEXT * _dp_sigmoid((sum_text / 100.0) - 1.0)
    q -= _ALPHA_LENGTH * (j - i + 1) / k

    # ── Navigability dampening ──
    # An atom with content but no navigable signal (link or media)
    # is not independently meaningful. Dampen it so the DP
    # prefers grouping it with adjacent navigable content.
    if sum_link == 0 and sum_media == 0:
        q *= 0.1

    return q


def _dp_segment_children(children):
    """Run 1D DP segmentation on a list of sibling nodes.

    Returns list of atom groups (each a list of nodes), or None
    if MDL rejects all partitions (molecule is atomic).

    The per-atom MDL penalty is incorporated directly into the DP
    recurrence: each additional atom must justify its existence by
    contributing quality that exceeds the penalty. This naturally
    penalizes over-segmentation (splitting into too many tiny atoms)
    while rewarding meaningful splits.

    Complexity: O(C²) where C = len(children).
    """
    k = len(children)
    if k < 2:
        return None

    # ── Feature extraction + prefix sums ──
    pfx_link = [0]
    pfx_heading = [0]
    pfx_media = [0]
    pfx_text = [0]
    pfx_content = [0]

    for child in children:
        f = _extract_child_features(child)
        pfx_link.append(pfx_link[-1] + f['link_count'])
        pfx_heading.append(pfx_heading[-1] + f['heading'])
        pfx_media.append(pfx_media[-1] + f['media_count'])
        pfx_text.append(pfx_text[-1] + f['text_len'])
        pfx_content.append(pfx_content[-1] + f['has_content'])

    def quality(i, j):
        return _atom_quality(i, j, k, pfx_link, pfx_heading,
                             pfx_media, pfx_text, pfx_content)

    # ── No-split baseline: treating entire sequence as 1 atom ──
    no_split_net = quality(0, k - 1) - _PER_ATOM_PENALTY

    # ── DP table with per-atom penalty in recurrence ──
    # OPT[j] = best net quality (Q - n×penalty) for children[0..j-1]
    opt = [float('-inf')] * (k + 1)
    opt[0] = 0.0
    backptr = [0] * (k + 1)

    for j in range(1, k + 1):
        for i in range(1, j + 1):
            q = quality(i - 1, j - 1)
            if q == float('-inf'):
                continue
            # Each atom pays a per-atom MDL penalty
            cand = opt[i - 1] + q - _PER_ATOM_PENALTY
            if cand > opt[j]:
                opt[j] = cand
                backptr[j] = i - 1

    # ── MDL acceptance: split must beat no-split ──
    if opt[k] <= no_split_net:
        return None

    # ── Backtrack ──
    atoms = []
    j = k
    while j > 0:
        i = backptr[j]
        atoms.append(children[i:j])
        j = i
    atoms.reverse()

    return atoms if len(atoms) >= 2 else None


def _find_split_parent(instance_node, max_depth=3):
    """Find the element whose direct children are content atoms.

    Uses 1D Dynamic Programming sequence segmentation to find the
    mathematically optimal partition of sibling nodes into content
    atoms. The DP cost function evaluates semantic density (links,
    headings, media, text mass) and applies an MDL stopping criterion
    to reject splits that do not compress the content description.

    Walks up to *max_depth* levels into the instance via BFS,
    evaluating each candidate parent's children through the DP
    segmenter. Returns (split_parent, atom_groups) or (None, []).

    Preserved structural guards:
      - All-<a> sibling detection (social link lists)
      - Media sibling guard (prevent orphaning image columns)
      - Depth preference (shallower splits preferred via quality penalty)
    """
    best_parent = None
    best_atoms = []
    best_depth = max_depth + 1
    best_quality = float('-inf')

    # BFS through limited depth
    queue = [(instance_node, 0)]
    visited = 0
    while queue and visited < 200:
        candidate, depth = queue.pop(0)
        visited += 1
        if depth > max_depth:
            continue

        children = list(
            c for c in (candidate.children
                        if hasattr(candidate, 'children') else [])
            if hasattr(c, 'tag') and not c.tag.startswith('#')
        )
        if len(children) < 2:
            for child in children:
                if hasattr(child, 'children'):
                    queue.append((child, depth + 1))
            continue

        # ── Preserved: All-<a> sibling detection (social links) ──
        if len(children) >= 2 and all(
            getattr(c, 'tag', '').lower() == 'a' for c in children
        ):
            valid = all(
                c.get_attr('href', '') and (
                    len(c.get_text().strip()) >= 1
                    or c.get_attr('aria-label', '')
                    or c.get_attr('title', '')
                    or any(getattr(d, 'tag', '').lower() == 'svg'
                           for d in c.iter_all())
                )
                for c in children
            )
            if valid:
                atoms = [[c] for c in children]
                if len(atoms) > 1:
                    best_parent = candidate
                    best_atoms = atoms
                    best_depth = depth
                    continue

        # ── Preserved: Media sibling guard ──
        if candidate.parent and depth > 0:
            _media_tags = {'img', 'picture', 'video'}
            sibling_has_media = False
            for sib in candidate.parent.children:
                if sib is candidate or not hasattr(sib, 'tag'):
                    continue
                if sib.tag.startswith('#'):
                    continue
                for desc in sib.iter_all():
                    if getattr(desc, 'tag', '').lower() in _media_tags:
                        sibling_has_media = True
                        break
                if sibling_has_media:
                    break
            if sibling_has_media:
                for child in children:
                    if hasattr(child, 'children'):
                        queue.append((child, depth + 1))
                continue

        # ── DP segmentation ──
        atoms = _dp_segment_children(children)

        if atoms is not None and len(atoms) > 1:
            # ── Atom independence gate ──
            # A valid molecule split requires that the proposed atoms
            # represent INDEPENDENT content items, not parts of ONE item.
            # The old heuristic enforced this implicitly via minimum counts:
            #   - heading-based: ≥ 2 children with headings
            #   - button-based:  ≥ 2 children with buttons
            #   - link-based:    ≥ 3 children with links
            # We replicate this as a post-DP validation.
            headed = 0    # atoms containing a heading
            buttoned = 0  # atoms containing a substantial button
            link_only = 0 # atoms with links but no heading/button
            for atom_group in atoms:
                a_heading = 0
                a_button = 0
                a_link = 0
                for node_in_atom in atom_group:
                    af = _extract_child_features(node_in_atom)
                    a_heading = max(a_heading, af['heading'])
                    a_button = max(a_button, af['button'])
                    a_link += af['link_count']
                if a_heading:
                    headed += 1
                elif a_button:
                    buttoned += 1
                elif a_link > 0:
                    link_only += 1

            gate_pass = (headed >= 2 or buttoned >= 2
                         or (link_only >= 3
                             and headed == 0 and buttoned == 0))
            if not gate_pass:
                # Split fails independence gate — not a true molecule
                for child in children:
                    if hasattr(child, 'children'):
                        queue.append((child, depth + 1))
                continue

            # Compute total quality with depth penalty for tie-breaking
            k = len(children)
            pfx_link = [0]
            pfx_heading = [0]
            pfx_media = [0]
            pfx_text = [0]
            pfx_content = [0]
            for child in children:
                f = _extract_child_features(child)
                pfx_link.append(pfx_link[-1] + f['link_count'])
                pfx_heading.append(pfx_heading[-1] + f['heading'])
                pfx_media.append(pfx_media[-1] + f['media_count'])
                pfx_text.append(pfx_text[-1] + f['text_len'])
                pfx_content.append(pfx_content[-1] + f['has_content'])

            total_q = 0.0
            offset = 0
            for atom_group in atoms:
                end = offset + len(atom_group) - 1
                total_q += _atom_quality(offset, end, k, pfx_link,
                                         pfx_heading, pfx_media,
                                         pfx_text, pfx_content)
                offset += len(atom_group)
            total_q -= depth * 0.3  # prefer shallower splits

            if total_q > best_quality:
                best_parent = candidate
                best_atoms = atoms
                best_depth = depth
                best_quality = total_q

        # Continue searching deeper
        for child in children:
            if hasattr(child, 'children'):
                queue.append((child, depth + 1))

    return best_parent, best_atoms


# ── Backward-compatible shims for test imports ────────────────────
# test_olympics.py and test_rollingstone.py import _count_headings.
# These thin wrappers delegate to the feature extractor.

def _count_headings(node):
    """Count heading elements with non-trivial text in subtree.

    Backward-compatible shim: delegates to _extract_child_features.
    """
    count = 0
    for desc in node.iter_all():
        if getattr(desc, 'tag', '').lower() in _HEADING_TAGS:
            if len(desc.get_text().strip()) >= 5:
                count += 1
    return count


def _count_content_links(node):
    """Count <a> elements with href and non-trivial text.

    Backward-compatible shim.
    """
    count = 0
    for desc in node.iter_all():
        if getattr(desc, 'tag', '').lower() == 'a':
            href = desc.get_attr('href', '') if hasattr(desc, 'get_attr') else ''
            text = desc.get_text().strip() if hasattr(desc, 'get_text') else ''
            if href and len(text) >= 3:
                count += 1
    return count


def _render_atom(atom_nodes, max_html=3000):
    """Render a list of sibling nodes as one atomic content unit."""
    parts = []
    for node in atom_nodes:
        mask = ContentCoagulator._build_dedup_mask(node)
        html = ContentCoagulator._render_deduped_html(
            node, max_length=max_html // max(len(atom_nodes), 1),
            mask=mask
        )
        if html.strip():
            parts.append(html)
    return '\n'.join(parts)


def _atom_text(atom_nodes, max_length=300):
    """Extract combined deduped text from atom nodes."""
    texts = []
    for node in atom_nodes:
        mask = ContentCoagulator._build_dedup_mask(node)
        t = ContentCoagulator._dedup_text(
            node, max_length=max_length // max(len(atom_nodes), 1),
            mask=mask
        )
        if t.strip():
            texts.append(t.strip())
    return ' '.join(texts)


def _split_br_entries(html_str):
    """Split rendered HTML containing <br>-delimited entries.

    Detects paragraphs where multiple content entries (each with a
    distinct link) are separated by double <br> sequences.  Returns
    a list of (html_fragment, text_preview) tuples, or an empty list
    if the HTML does not match the pattern.
    """
    # Must have 2+ distinct <a> hrefs
    hrefs = set(re.findall(r'<a\s[^>]*href="([^"]+)"', html_str))
    if len(hrefs) < 2:
        return []

    # Must have double-<br> delimiter pattern (handles <br>, <br/>, <br></br>)
    if not re.search(r'(?:<br[^>]*>(?:</br>)?[\s\n]*){2,}',
                      html_str, re.IGNORECASE):
        return []

    # Split on double-<br> (with optional </br> and whitespace)
    fragments = re.split(
        r'(?:<br[^>]*>(?:</br>)?[\s\n]*){2,}', html_str, flags=re.IGNORECASE
    )

    # Each fragment must have meaningful content
    entries = []
    for frag in fragments:
        text = re.sub(r'<[^>]+>', '', frag).strip()
        if len(text) < 5:
            continue
        entries.append((frag.strip(), text[:120]))

    # Only split if we get 2+ entries
    if len(entries) < 2:
        return []

    return entries


def build_chunk_html(dom, chunk, title_prefix=''):
    """Build HTML for a single chunk with deduped instance rendering."""
    is_cist = getattr(chunk, '_parent_chunk_id', -1) >= 0
    cist_label = (' <span class="cist-tag">[sub-template]</span>'
                  if is_cist else '')

    lines = [
        '<!DOCTYPE html>',
        '<html><head><meta charset="utf-8">',
        f'<title>{title_prefix}Chunk {chunk.chunk_id} — '
        f'{chunk.frequency} instances</title>',
        '<style>',
        _CSS,
        '</style>',
        '</head><body>',
        f'<h2>Chunk {chunk.chunk_id}{cist_label}</h2>',
        f'<p>Signature: <code>{chunk.signature[:120]}</code></p>',
        f'<p>Container: <code>{chunk.subtree_root}</code></p>',
        f'<p>Instances: {chunk.frequency}</p>',
        '<hr>',
    ]

    seen_texts = set()
    rendered = 0
    for path in chunk.trie_paths:
        node = dom.xpath_one(path)
        if not node:
            continue

        # ── Molecule detection: split multi-atom instances ──
        split_parent, atoms = _find_split_parent(node)
        if atoms and len(atoms) > 1:
            # Recursively try splitting each atom further (1 level)
            final_atoms = []
            for atom_nodes in atoms:
                if len(atom_nodes) == 1:
                    sub_parent, sub_atoms = _find_split_parent(atom_nodes[0])
                    if sub_atoms and len(sub_atoms) > 1:
                        final_atoms.extend(sub_atoms)
                        continue
                final_atoms.append(atom_nodes)

            for atom_nodes in final_atoms:
                atom_html = _render_atom(atom_nodes)
                atom_text = _atom_text(atom_nodes)
                if not atom_html.strip():
                    continue
                text_key = ' '.join(atom_text.split()).lower()[:200]
                if text_key and len(text_key) >= 20:
                    if text_key in seen_texts:
                        continue
                    seen_texts.add(text_key)
                rendered += 1
                text_preview = atom_text[:120].replace('\n', ' ')
                lines.append('<div class="instance">')
                lines.append(
                    f'  <div class="instance-header">{path}'
                    f' [atom]</div>')
                lines.append(f'  {atom_html}')
                if text_preview:
                    lines.append(
                        f'  <div class="instance-meta">'
                        f'text: {text_preview}</div>')
                lines.append('</div>')
            continue

        # ── Normal (atomic) instance rendering ──
        _, html, text = _render_instance(dom, path)

        # ── Fallback: split <br>-delimited entries ──
        br_entries = _split_br_entries(html)
        if br_entries:
            for frag_html, frag_text in br_entries:
                text_key = ' '.join(frag_text.split()).lower()[:200]
                if text_key and len(text_key) >= 20:
                    if text_key in seen_texts:
                        continue
                    seen_texts.add(text_key)
                rendered += 1
                lines.append('<div class="instance">')
                lines.append(
                    f'  <div class="instance-header">{path}'
                    f' [br-split]</div>')
                lines.append(f'  {frag_html}')
                if frag_text:
                    lines.append(
                        f'  <div class="instance-meta">'
                        f'text: {frag_text}</div>')
                lines.append('</div>')
            continue

        # Skip instances whose deduped text is identical to one
        # already rendered (catches dual-rendering DOM copies)
        text_key = ' '.join(text.split()).lower()[:200]
        if text_key and len(text_key) >= 20 and text_key in seen_texts:
            continue
        if len(text_key) >= 20:
            seen_texts.add(text_key)

        rendered += 1
        text_preview = text[:120].replace('\n', ' ').strip()
        lines.append('<div class="instance">')
        lines.append(f'  <div class="instance-header">{path}</div>')
        lines.append(f'  {html}')
        if text_preview:
            lines.append(
                f'  <div class="instance-meta">text: {text_preview}</div>'
            )
        lines.append('</div>')

    # Update instance count to reflect deduped count
    lines[10] = (
        f'<p>Instances: {chunk.frequency} '
        f'({rendered} unique after dedup)</p>'
    )

    lines.append('</body></html>')
    return '\n'.join(lines)


def build_functional_chunk_html(dom, chunk, scorer, title):
    """Build HTML for a functional chunk (search/pagination)."""
    scored = []
    for xpath in chunk.trie_paths:
        node = dom.xpath_one(xpath)
        if node:
            score = scorer.score_node(node)
            scored.append((score, node, xpath))
    scored.sort(key=lambda x: -x[0])

    lines = [
        '<!DOCTYPE html>',
        '<html><head><meta charset="utf-8">',
        f'<title>{title} — {len(scored)} elements</title>',
        '<style>',
        _CSS,
        '  .score { font-size: 0.75em; color: #1565c0; }',
        '</style>',
        '</head><body>',
        f'<h2>{title}</h2>',
        f'<p>Elements: {len(scored)}</p>',
        '<hr>',
    ]
    for score, node, xpath in scored:
        lines.append('<div class="instance">')
        lines.append(f'  <div class="instance-header">{xpath} '
                     f'<span class="score">[score: {score}]</span></div>')
        lines.append(f'  {node.to_html(indent=1)}')
        lines.append('</div>')
    lines.append('</body></html>')
    return '\n'.join(lines)


def build_unified_html(dom, chunks):
    """Build single HTML with all chunks using deduped rendering."""
    structural = [ch for ch in chunks if ch._structural_sig]
    text_chunks = [ch for ch in chunks
                   if ch.signature.startswith('[text_content:')
                   or ch.signature.startswith('[nav_content:')]
    search = next((ch for ch in chunks
                   if ch.signature == '[search_inputs]'), None)
    pagination = next((ch for ch in chunks
                       if ch.signature == '[pagination_buttons]'), None)

    total = sum(ch.frequency for ch in structural + text_chunks)

    # Separate top-level and CIST sub-template chunks
    top_level = [ch for ch in structural
                 if getattr(ch, '_parent_chunk_id', -1) < 0]
    cist = [ch for ch in structural
            if getattr(ch, '_parent_chunk_id', -1) >= 0]

    lines = [
        '<!DOCTYPE html>',
        '<html><head><meta charset="utf-8">',
        '<title>Distilled Chunks</title>',
        '<style>',
        _CSS,
        '  .chunk-separator { border: 2px solid #333; '
        'margin: 24px 0 8px 0; }',
        '  .score { font-size: 0.75em; color: #1565c0; }',
        '  .cist-tag { color: #d84315; font-weight: bold; }',
        '</style>',
        '</head><body>',
        '<h1>Distilled Chunks</h1>',
        f'<p>{len(top_level)} top-level + {len(cist)} sub-template '
        f'structural chunks, {len(text_chunks)} text chunks, '
        f'{total} total instances</p>',
    ]

    # — Top-level structural chunks —
    for ch in top_level:
        _append_chunk_section(lines, dom, ch)

    # — CIST sub-templates —
    if cist:
        lines.append('<hr class="chunk-separator">')
        lines.append(
            '<h2 style="color:#d84315">Sub-Template Chunks</h2>')
        for ch in cist:
            _append_chunk_section(lines, dom, ch, is_cist=True)

    # — Text content chunks —
    for ch in text_chunks:
        lines.append('<hr class="chunk-separator">')
        lines.append(f'<h2>{ch.signature}</h2>')
        lines.append(f'<p>Instances: {ch.frequency}</p>')
        lines.append('<hr>')
        for path in ch.trie_paths:
            node = dom.xpath_one(path)
            if node:
                lines.append('<div class="instance">')
                lines.append(
                    f'  <div class="instance-header">{path}</div>')
                lines.append(f'  {node.to_html(indent=1)}')
                lines.append('</div>')

    # — Search inputs —
    if search:
        _append_functional_section(
            lines, dom, search, SearchInputCollector.VOCABULARY,
            'Search Inputs'
        )

    # — Pagination/buttons —
    if pagination:
        _append_functional_section(
            lines, dom, pagination, PaginationCollector.VOCABULARY,
            'Pagination &amp; Buttons'
        )

    lines.append('</body></html>')
    return '\n'.join(lines)


def _append_chunk_section(lines, dom, ch, is_cist=False):
    """Add a chunk's deduped instances to the unified HTML."""
    cist_label = (' <span class="cist-tag">[sub-template]</span>'
                  if is_cist else '')

    lines.append('<hr class="chunk-separator">')
    lines.append(f'<h2>Chunk {ch.chunk_id}{cist_label}</h2>')
    lines.append(
        f'<p>Signature: <code>{ch.signature[:120]}</code></p>')
    lines.append(
        f'<p>Container: <code>{ch.subtree_root}</code></p>')

    seen_texts = set()
    rendered = 0
    for path in ch.trie_paths:
        node = dom.xpath_one(path)
        if not node:
            continue

        # ── Molecule detection ──
        split_parent, atoms = _find_split_parent(node)
        if atoms and len(atoms) > 1:
            for atom_nodes in atoms:
                atom_html = _render_atom(atom_nodes)
                atom_text = _atom_text(atom_nodes)
                if not atom_html.strip():
                    continue
                text_key = ' '.join(atom_text.split()).lower()[:200]
                if text_key and len(text_key) >= 20:
                    if text_key in seen_texts:
                        continue
                    seen_texts.add(text_key)
                rendered += 1
                text_preview = atom_text[:120].replace('\n', ' ')
                lines.append('<div class="instance">')
                lines.append(
                    f'  <div class="instance-header">{path}'
                    f' [atom]</div>')
                lines.append(f'  {atom_html}')
                if text_preview:
                    lines.append(
                        f'  <div class="instance-meta">'
                        f'text: {text_preview}</div>')
                lines.append('</div>')
            continue

        # ── Normal rendering ──
        _, html, text = _render_instance(dom, path)
        if not html:
            continue

        # ── Fallback: split <br>-delimited entries ──
        br_entries = _split_br_entries(html)
        if br_entries:
            for frag_html, frag_text in br_entries:
                text_key = ' '.join(frag_text.split()).lower()[:200]
                if text_key and len(text_key) >= 20:
                    if text_key in seen_texts:
                        continue
                    seen_texts.add(text_key)
                rendered += 1
                lines.append('<div class="instance">')
                lines.append(
                    f'  <div class="instance-header">{path}'
                    f' [br-split]</div>')
                lines.append(f'  {frag_html}')
                if frag_text:
                    lines.append(
                        f'  <div class="instance-meta">'
                        f'text: {frag_text}</div>')
                lines.append('</div>')
            continue

        text_key = ' '.join(text.split()).lower()[:200]
        if text_key and len(text_key) >= 20 and text_key in seen_texts:
            continue
        if len(text_key) >= 20:
            seen_texts.add(text_key)

        rendered += 1
        text_preview = text[:120].replace('\n', ' ').strip()
        lines.append('<div class="instance">')
        lines.append(
            f'  <div class="instance-header">{path}</div>')
        lines.append(f'  {html}')
        if text_preview:
            lines.append(
                f'  <div class="instance-meta">'
                f'text: {text_preview}</div>'
            )
        lines.append('</div>')

    lines.append(
        f'<p>Instances: {ch.frequency} '
        f'({rendered} unique after dedup)</p>'
    )
    lines.append('<hr>')


def _append_functional_section(lines, dom, chunk, vocabulary, title):
    """Add a functional chunk (search/pagination) to unified HTML."""
    scorer = _VocabularyScorer(vocabulary)
    scored = []
    for xpath in chunk.trie_paths:
        node = dom.xpath_one(xpath)
        if node:
            score = scorer.score_node(node)
            scored.append((score, node, xpath))
    scored.sort(key=lambda x: -x[0])

    lines.append('<hr class="chunk-separator">')
    lines.append(f'<h2>{title}</h2>')
    lines.append(f'<p>Elements: {len(scored)}</p>')
    lines.append('<hr>')

    for score, node, xpath in scored:
        lines.append('<div class="instance">')
        lines.append(
            f'  <div class="instance-header">{xpath} '
            f'<span class="score">[score: {score}]</span></div>')
        lines.append(f'  {node.to_html(indent=1)}')
        lines.append('</div>')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    html_file = sys.argv[1]
    with open(html_file, 'r', encoding='utf-8', errors='replace') as f:
        html_content = f.read()

    stem = Path(html_file).stem
    out_dir = Path(f'./distilled_{stem}')
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'\nProcessing: {html_file}')
    distiller = WebDistiller(html_content)
    chunks = distiller.process(verbose=True)

    if not chunks:
        print('No structures found.')
        return

    structural = [ch for ch in chunks if ch._structural_sig]
    text_ch = [ch for ch in chunks
               if ch.signature.startswith('[text_content:')
               or ch.signature.startswith('[nav_content:')]
    search_chunk = next(
        (ch for ch in chunks if ch.signature == '[search_inputs]'),
        None)
    pagination_chunk = next(
        (ch for ch in chunks
         if ch.signature == '[pagination_buttons]'), None)

    top_level = [ch for ch in structural
                 if getattr(ch, '_parent_chunk_id', -1) < 0]
    cist = [ch for ch in structural
            if getattr(ch, '_parent_chunk_id', -1) >= 0]

    total_inst = sum(ch.frequency for ch in structural + text_ch)
    print(f'\n{len(top_level)} top-level + {len(cist)} sub-template '
          f'structural + {len(text_ch)} text chunks, '
          f'{total_inst} instances')

    # — Unified file —
    unified = build_unified_html(distiller.dom, chunks)
    (out_dir / 'distilled.html').write_text(
        unified, encoding='utf-8')
    print(f'  → {out_dir}/distilled.html')

    # — Per-chunk files —
    for ch in structural + text_ch:
        html = build_chunk_html(distiller.dom, ch)
        fname = f'chunk_{ch.chunk_id:03d}.html'
        (out_dir / fname).write_text(html, encoding='utf-8')
    print(f'  → {out_dir}/chunk_*.html '
          f'({len(structural) + len(text_ch)} files)')

    # — Functional chunk files —
    if search_chunk:
        scorer = _VocabularyScorer(SearchInputCollector.VOCABULARY)
        html = build_functional_chunk_html(
            distiller.dom, search_chunk, scorer, 'Search Inputs')
        (out_dir / 'search.html').write_text(
            html, encoding='utf-8')
        print(f'  → {out_dir}/search.html '
              f'({search_chunk.frequency} elements)')
    else:
        print('  (no search inputs found)')

    if pagination_chunk:
        scorer = _VocabularyScorer(PaginationCollector.VOCABULARY)
        html = build_functional_chunk_html(
            distiller.dom, pagination_chunk, scorer,
            'Pagination &amp; Buttons')
        (out_dir / 'pagination.html').write_text(
            html, encoding='utf-8')
        print(f'  → {out_dir}/pagination.html '
              f'({pagination_chunk.frequency} elements)')
    else:
        print('  (no pagination elements found)')

    print('\n✅ Done.')


if __name__ == '__main__':
    main()
