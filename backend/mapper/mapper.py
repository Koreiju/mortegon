"""
mapper.py — SLAM‑inspired DOM lifecycle orchestrator.

Pipeline:  scan → distill → layout → stream → release

The mapper coordinates between:
  - Selenium WebDriver (live browser)
  - dom_distiller scanner (pure scan + merge‑tree dedup)
  - dom_distiller ShadowDOM parser (parse HTML → object model)
  - dom_distiller ContentTagger (extract content xpaths + categories)
  - SnapshotStore (persist HTML files + DB records)
  - LabelEngine (labels, commutation, LCA, structure tags)
  - LayoutGenerator (3D radial‑tree coordinates from tree structure)
  - GUI WebSocket stream (push full node sets to frontend)

Key design: the layout tree is built from the Patricia trie of content‑bearing
nodes only, with content categories attached as metadata. Edges in the 3D GUI
follow the Patricia trie parent‑child structure.
"""

from __future__ import annotations

import logging
import time
import uuid
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable, Set, Tuple

from backend.dom.shadow_html_parser import ShadowDOM, get_absolute_xpath
from backend.dom.content_tagger import ContentTagger, TaggedContent
from backend.dom.xpath_tree_builder import XPathTreeBuilder, count_content_nodes
from backend.dom.scanner import ShadowDOMScanner, serialize_to_html
from backend.dom.web_distiller_freq import ContentCoagulator

from backend.mapper.snapshot_store import SnapshotStore
from backend.mapper.label_engine import LabelEngine, generalize_xpath
from backend.mapper.chunk_builder import (
	ChunkBuilder,
	build_xpath_node_map,
	build_text_provider_from_dom,
	build_structure_provider_from_dom,
	Chunk,
	DEFAULT_CHAR_BUDGET,
	HARD_CHAR_LIMIT,
)
from backend.mapper.chunk_render import (
	render_all_chunks,
	render_chunk_instances,
	_serialize_html,
	build_gen_xpath_map
)
from backend.mapper.chunk_absorber import ChunkAbsorber
from backend.mapper.console_reporter import make_console_stream
from backend.services.global_tfidf_store import get_default_store, ChunkMeta
from backend.mapper.dedup_logging import get_dedup_logger, DedupStatsCollector
from sortedcontainers import SortedList
from backend.mapper.pipeline_runner import (
	SnapshotPipeline,
	_ChunkBatch,
	_StreamBatch,
)
from backend.mapper.pipeline_config import get_config as _get_pipeline_config
from backend.ontology.layout_generator import LayoutGenerator
from backend.ontology.type_handlers import TypeHandlerRegistry
from backend.ontology.interactive_ranker import InteractiveRanker
import multiprocessing

import os as _os
import numpy as np
import re

def _xpath_depth(xp: str) -> int:
	return xp.count('/')


# URL-path tokenizer used to enrich TF-IDF input. ``/details/
# softwarelibrary_msdos_games`` → ``details softwarelibrary msdos games``.
# Underscores, hyphens, query-string separators and common stop-tokens
# (`www`, `http`, `html`, etc.) are dropped so the bag matches a human
# query like "MS-DOS games" instead of leaking the raw slug.
_URL_TOK_SPLIT = re.compile(r"[/?&#=.:_\-]+")
_URL_TOK_STOP = frozenset({
	"http", "https", "www", "html", "htm", "php", "aspx", "jsp",
	"index", "amp", "ref", "utm", "id", "page", "pages",
	"com", "org", "net", "io", "co", "uk", "edu", "gov",
	"jpg", "jpeg", "png", "gif", "svg", "webp", "mp4", "mp3", "pdf",
	"static", "assets", "cdn", "images", "img", "media",
})


def _tokenize_url_path(raw: str, limit: int = 12) -> str:
	"""Return a space-joined bag of meaningful tokens from a URL string."""
	if not raw:
		return ""
	core = raw.split("?", 1)[0].split("#", 1)[0]
	parts = [p.lower() for p in _URL_TOK_SPLIT.split(core) if p]
	keep: list = []
	seen: set = set()
	for p in parts:
		if p in _URL_TOK_STOP or p.isdigit() or len(p) < 3 or p in seen:
			continue
		seen.add(p)
		keep.append(p)
		if len(keep) >= limit:
			break
	return " ".join(keep)


def _reassemble_distilled_html(url: str, chunks_by_xpath: Dict[str, str]) -> str:
	"""Stitch per-chunk HTML fragments into a single distilled document.

	Each fragment is keyed by its representative absolute xpath, which
	includes ``#shadow-root`` markers and ``[N]`` indices, matching the
	source DOM. We emit a minimal ``<html><body>`` shell and order the
	fragments by xpath depth then string order so the resulting HTML
	preserves document order — generalized xpaths from the Patricia
	trie still navigate the same coordinates inside the saved file.

	When two chunk fragments overlap (one is a descendant of another),
	we keep the deeper one (which the chunker selected as a tight card
	root) and skip the broader one rather than nest fragments — the
	chunker's claim logic already enforces non-overlapping members, so
	this is mostly defensive.
	"""
	if not chunks_by_xpath:
		return f"<!doctype html><html><head><title>distilled: {url}</title></head><body></body></html>"
	# Drop fragments whose xpath is a strict prefix of another fragment.
	xpaths = sorted(chunks_by_xpath.keys())
	keep: List[Tuple[str, str]] = []
	used: Set[str] = set()
	for xp in xpaths:
		# Skip if any already-kept entry is a prefix of this one (we
		# prefer deeper specifically-selected chunk roots) — actually
		# the inverse: skip if THIS xpath is a prefix of a deeper one
		# we'll see later. Since xpaths are sorted lex, descendants of
		# ``/html/body[1]/x`` appear AFTER it; check if any later xpath
		# starts with our path + '/'.
		is_prefix_of_later = any(
			xp != other and other.startswith(xp + "/") for other in xpaths
		)
		if is_prefix_of_later:
			continue
		keep.append((xp, chunks_by_xpath[xp]))
		used.add(xp)
	# Sort kept fragments by their xpath segment-array so document
	# order is preserved across the page.
	def _depth_key(item):
		xp, _ = item
		return (xp.count("/"), xp)
	keep.sort(key=_depth_key)
	body_parts = [html for _xp, html in keep]
	return (
		"<!doctype html><html><head>"
		f"<title>distilled: {url}</title>"
		"<meta charset='utf-8'>"
		"</head><body>\n"
		+ "\n".join(body_parts)
		+ "\n</body></html>"
	)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hash helpers — mirror the djb2 / rotL / hashFields functions in the JS
# extraction scripts so Python can recompute ancestor hashes after removals.
# ---------------------------------------------------------------------------

def _dense_proxy_embedding(text: str, dim: int = 1024) -> list:
	"""Deterministic unit vector from text hash — lightweight placeholder."""
	if not text:
		return [0.0] * dim
	seed = int(hashlib.md5(text.encode()).hexdigest(), 16) & 0xFFFFFFFF
	rng = np.random.default_rng(seed)
	vec = rng.normal(0.0, 1.0 / np.sqrt(dim), size=dim).astype(np.float32)
	norm = float(np.linalg.norm(vec))
	return (vec / norm).tolist() if norm > 0 else [0.0] * dim

def _djb2_py(s: str) -> int:
	"""djb2 hash (matches JS djb2 helper in EXTRACT_UNIFIED_JS)."""
	h = 5381
	for c in s:
		h = (((h << 5) + h) + ord(c)) & 0xFFFFFFFF
	return h


def _rot_l_32_py(n: int, k: int) -> int:
	"""32‑bit left rotation (matches JS rotL helper)."""
	n = n & 0xFFFFFFFF
	return ((n << k) | (n >> (32 - k))) & 0xFFFFFFFF


def _hash_fields_py(fields: Dict[str, str]) -> int:
	"""Recompute content_hash from a content_fields dict (matches JS hashFields)."""
	keys = sorted(fields.keys())
	s = ""
	for k in keys:
		v = str(fields.get(k, ""))
		s += k + "=" + (v[:20] if len(v) > 20 else v) + "|"
	return _djb2_py(s)


# ---------------------------------------------------------------------------
# Lightweight proxy/instance types for the delta‑path TF‑IDF pipeline batch.
# ---------------------------------------------------------------------------

class _DeltaChunkProxy:
	"""Thin wrapper so bottom‑up chunk dicts satisfy pipeline attribute access."""
	__slots__ = ("_d",)

	def __init__(self, d: dict) -> None:
		self._d = d

	def __getattr__(self, name: str):
		return self._d.get(name)

	def as_dict(self) -> dict:
		return self._d


class _DeltaInstanceLight:
	"""Minimal ChunkInstance for TF‑IDF vectorisation + kuzu persistence."""
	__slots__ = (
		"chunk_id", "rendered_text", "absolute_xpath",
		"instance_idx", "pattern", "embedding",
		"html_raw", "fields",
	)

	def __init__(
		self, *, chunk_id: str, rendered_text: str,
		absolute_xpath: str, instance_idx: int,
		pattern: str, html_raw: str = "",
		fields: Optional[Dict[str, Any]] = None,
	) -> None:
		self.chunk_id = chunk_id
		self.rendered_text = rendered_text
		self.absolute_xpath = absolute_xpath
		self.instance_idx = instance_idx
		self.pattern = pattern
		self.html_raw = html_raw
		self.fields = fields or {}
		self.embedding = None

	def instance_id(self, url: str) -> str:
		base = self.chunk_id
		if self.absolute_xpath:
			suffix = hashlib.md5(self.absolute_xpath.encode()).hexdigest()[:8]
		else:
			suffix = str(self.instance_idx)
		return f"{base}_{suffix}"


SPARSE_INDEX_DIR = _os.path.normpath(
	_os.path.join(
		_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
		"..", "snapshots", "tfidf_indexes",
	)
)


class DomMapper:
	"""
	Central orchestrator for the DOM scan/map/render pipeline.

	Lifecycle per snapshot (via snapshot()):
	  1. scan()     — extract DOM from live browser via Selenium
	  2. distill()  — parse HTML → ShadowDOM → content tags → Patricia trie
	  3. layout()   — compute deterministic radial‑tree 3D coordinates
	  4. stream()   — push full node set to GUI via WebSocket callback
	  5. release()  — free DOM object from memory

	Optional standalone methods:
	  - register()  — save HTML to disk, register in DB (merge‑conscious)
	  - analyze()   — WL coloring + template grouping (enriches stream payload)

	The mapper tracks all registered URLs and their snapshots,
	acting as the "map" in the SLAM analogy.
	"""

	def __init__(self, driver=None):
		self.driver = driver
		self.store = SnapshotStore()
		self.labels = LabelEngine()
		self._dedup_stats = DedupStatsCollector()

		self._delta_lock = threading.Lock()

		# In‑memory cache (released after streaming)
		self._active_doms: Dict[str, ShadowDOM] = {}
		self._active_trees: Dict[str, Dict] = {}
		self._active_tagged: Dict[str, TaggedContent] = {}
		self._active_layouts: Dict[str, List[Dict]] = {}
		self._active_analytics: Dict[str, Dict] = {}
		self._active_chunks: Dict[str, List[Chunk]] = {}

		self._active_scanner: Optional[Any] = None
		self._billboard_cache: Dict[str, Dict[str, Any]] = {}

		self._active_xpath_maps: Dict[str, Dict[str, Any]] = {}
		self._active_text_providers: Dict[str, Any] = {}
		self._active_structure_providers: Dict[str, Any] = {}

		self._delta_pattern_chunks: Dict[str, List[dict]] = {}
		self._delta_chunk_ledger: Dict[str, Set[str]] = {}
		self._delta_claimed: Dict[str, str] = {}

		# Persistent per-URL cache for search — survives release()
		self._last_dom_for_url: Dict[str, ShadowDOM] = {}
		self._last_tree_for_url: Dict[str, Dict] = {}
		self._last_snapshot_for_url: Dict[str, str] = {}
		self._content_hash_for_url: Dict[str, str] = {}

		self._active_scanner: Optional[Any] = None
		self._billboard_cache: Dict[str, Dict[str, Any]] = {}

		self._active_xpath_maps: Dict[str, Dict[str, Any]] = {}
		self._active_text_providers: Dict[str, Any] = {}
		self._active_structure_providers: Dict[str, Any] = {}

	# ------------------------------------------------------------------
	# 1. SCAN — extract DOM from live browser
	# ------------------------------------------------------------------

	def scan(self, url: str, max_duration: int = 60, pause: float = 1.0) -> Any:
		if not self.driver:
			raise RuntimeError("No WebDriver attached to mapper")
		scanner = ShadowDOMScanner(self.driver)
		return scanner.scan(url, max_duration=max_duration, pause=pause)

	# ------------------------------------------------------------------
	# 2. REGISTER — save to DB (merge‑conscious)
	# ------------------------------------------------------------------

	def register(self, url: str, html: str, snapshot_id: str = None) -> Tuple[str, bool]:
		sid, is_new = self.store.save_snapshot(url, html, snapshot_id)
		logger.info(f"[Mapper] Registered snapshot {sid} (new={is_new}) for {url}")
		return sid, is_new

	# ------------------------------------------------------------------
	# 3. DISTILL — parse → tag → build FULL DOM tree
	# ------------------------------------------------------------------

	def distill(self, snapshot_id: str, url: str, html: str = None, persist: bool = True) -> Dict[str, Any]:
		if html is None:
			t0 = time.time()
			html = self.store.load_snapshot_html(snapshot_id)
			if html is None:
				raise ValueError(f"No HTML found for snapshot {snapshot_id}")
			logger.info(f"[Profiler] load_snapshot_html: {time.time() - t0:.4f}s")

		logger.info(f"[Mapper] Parsing {len(html)} bytes into ShadowDOM...")
		t1 = time.time()
		dom = ShadowDOM(html)
		self._active_doms[snapshot_id] = dom
		logger.info(f"[Profiler] ShadowDOM parse: {time.time() - t1:.4f}s")

		try:
			t_mask = time.time()
			dedup_mask = ContentCoagulator._build_dedup_mask(dom.root)
			logger.info(f"[Profiler] Semantic dedup mask: {time.time() - t_mask:.4f}s (Masked {len(dedup_mask)} nodes)")
		except Exception as e:
			logger.warning(f"Failed to build dedup mask: {e}")
			dedup_mask = set()

		logger.info("[Mapper] Running content tagger...")
		t2 = time.time()
		tagger = ContentTagger(dom, mask=dedup_mask)
		tagged = tagger.tag()
		self._active_tagged[snapshot_id] = tagged
		logger.info(f"[Profiler] ContentTagger: {time.time() - t2:.4f}s")

		content_count = len(tagged.all_content_xpaths())
		logger.info(f"[Mapper] Found {content_count} content xpaths, {len(tagged.all_tags)} total tags")

		logger.info("[Mapper] Building content xpath tree for DB...")
		t3 = time.time()
		builder = XPathTreeBuilder()
		builder.add_tagged_content(tagged)
		content_tree = builder.build()
		self._active_trees[snapshot_id] = content_tree
		logger.info(f"[Profiler] XPathTreeBuilder: {time.time() - t3:.4f}s")

		content_nodes = count_content_nodes(content_tree)
		logger.info(f"[Mapper] Distilled tree: {content_nodes} content nodes")

		if persist:
			t4 = time.time()
			self.store.save_content_tree(snapshot_id, url, content_tree)
			logger.info(f"[Profiler] DB persist tree: {time.time() - t4:.4f}s")

		return content_tree

	# ------------------------------------------------------------------
	# 4. LAYOUT — compute 3D coordinates from full tree
	# ------------------------------------------------------------------

	def layout(self, snapshot_id: str, offset_x: float = 0.0) -> List[Dict[str, Any]]:
		content_tree = self._active_trees.get(snapshot_id)
		if content_tree is None:
			content_tree = self.store.load_content_tree(snapshot_id)
			if content_tree is None:
				raise ValueError(f"No tree for snapshot {snapshot_id}")

		t0 = time.time()
		layout_struct = self._tree_to_layout_struct(content_tree)
		logger.info(f"[Profiler] tree_to_layout_struct: {time.time() - t0:.4f}s")

		t_prune = time.time()
		self._prune_contentless_branches(layout_struct)
		logger.info(f"[Profiler] prune_contentless_branches: {time.time() - t_prune:.4f}s")

		t_layout = time.time()
		LayoutGenerator.apply_radial_tree_layout(layout_struct)
		bounding_radius = LayoutGenerator.compute_bounding_radius(layout_struct)
		logger.info(f"[Profiler] radial_tree_layout: {time.time() - t_layout:.4f}s (bounding_radius={bounding_radius:.1f})")

		t2 = time.time()
		flat = self._flatten_layout(layout_struct, offset_x, bounding_radius)
		self._active_layouts[snapshot_id] = flat
		logger.info(f"[Profiler] flatten_layout: {time.time() - t2:.4f}s")
		logger.info(f"[Mapper] Layout: {len(flat)} nodes")
		return flat

	# ------------------------------------------------------------------
	# 5. STREAM — push to GUI via callback
	# ------------------------------------------------------------------

	def stream(self, snapshot_id: str, url: str, callback: Callable, is_final: bool = True) -> None:
		flat = self._active_layouts.get(snapshot_id)
		if flat is None:
			raise ValueError(f"No layout computed for {snapshot_id}")

		dom = self._active_doms.get(snapshot_id)
		if dom is None:
			html = self.store.load_snapshot_html(snapshot_id)
			if html:
				dom = ShadowDOM(html)

		xpath_to_node = {}
		if dom:
			for n in dom.iter_all():
				try:
					xp = get_absolute_xpath(n)
					if xp:
						xpath_to_node[xp] = n
				except Exception:
					pass

		registry = TypeHandlerRegistry(base_url=url)
		ranker = InteractiveRanker()

		typed_nodes = []
		for node in flat:
			xpath = node.get('xpath', '')
			text_content = ''
			raw_attrs = {}
			if dom and xpath and xpath != '/':
				real_node = xpath_to_node.get(xpath)
				if real_node:
					text_content = real_node.get_text(recursive=True, separator=" ").strip()
					try:
						raw_attrs = real_node.get_all_attrs()
					except Exception:
						pass
			node['text'] = text_content
			node['attributes'] = raw_attrs
			raw_dict = {
				'xpath': xpath,
				'tagName': node.get('tag', ''),
				'depth': node.get('depth', 0),
				'textContent': text_content,
				'attributes': raw_attrs
			}
			typed_node = registry.convert_node(raw_dict)
			typed_node._flat_ref = node
			typed_nodes.append(typed_node)

		ranker.rank_search_inputs(typed_nodes)
		ranker.rank_pagination_controls(typed_nodes)

		analytics = self._active_analytics.get(snapshot_id, {})
		colored_nodes = analytics.get('colored_nodes', {})
		template_groups = analytics.get('template_groups', [])
		xpath_to_node_id = analytics.get('xpath_to_node_id', {})

		labels_map: Dict[str, str] = {}
		try:
			for row in self.labels.get_labels_for_url(url):
				xp = row.get('xpath')
				lbl = row.get('label')
				if xp and lbl:
					labels_map[xp] = lbl
		except Exception as e:
			logger.debug(f"[Mapper] labels bulk‑fetch skipped: {e}")

		chunk_lookup: Dict[str, Dict[str, Any]] = {}
		active_chunks = self._active_chunks.get(snapshot_id) or []
		if not active_chunks:
			try:
				for row in self.store.load_chunks(snapshot_id):
					for xp in row.get('member_xpaths', []):
						chunk_lookup[xp] = {
							'chunk_id': row['chunk_id'],
							'chunk_pattern': row['pattern'],
							'chunk_label': row.get('label'),
							'chunk_char_count': row.get('char_count', 0),
							'chunk_commutation_count': row.get('commutation_count', 0),
							'is_chunk_root': (xp == row.get('representative_xpath')),
						}
			except Exception as e:
				logger.debug(f"[Mapper] chunk lookup (DB) skipped: {e}")
		else:
			for ch in active_chunks:
				for xp in ch.member_xpaths:
					chunk_lookup[xp] = {
						'chunk_id': ch.chunk_id,
						'chunk_pattern': ch.pattern,
						'chunk_label': ch.label,
						'chunk_char_count': ch.char_count,
						'chunk_commutation_count': ch.commutation_count,
						'is_chunk_root': (xp == ch.representative_xpath),
					}

		tg_lookup: Dict[int, Dict] = {}
		for tg in template_groups:
			pq_sig = tg.pq_tree.canonical() if getattr(tg, 'pq_tree', None) else None
			tier = getattr(tg, 'tier', None)
			tier_str = tier.name if hasattr(tier, 'name') else str(tier) if tier else None
			for cn in getattr(tg, 'instances', []):
				nid = getattr(cn.node, 'node_id', None) or id(cn.node)
				tg_lookup[nid] = {
					'template_group_id': tg.group_id,
					'template_tier': tier_str,
					'pq_signature': pq_sig,
				}

		nodes = []
		links = []
		for typed_node in typed_nodes:
			node = typed_node._flat_ref
			node_xpath = typed_node.xpath
			node_id = f"{url}:{node_xpath}"

			tag = typed_node.tag.value if hasattr(typed_node.tag, 'value') else str(typed_node.tag)
			attrs = typed_node.raw_attrs
			display_name = tag
			if 'id' in attrs:
				display_name = f"{tag}#{attrs['id']}"
			elif typed_node.class_names:
				display_name = f"{tag}.{typed_node.class_names[0]}"

			node_dict = {
				'id': node_id,
				'xpath': node_xpath,
				'name': display_name,
				'tag': tag,
				'categories': node.get('categories', []),
				'attributes': attrs,
				'text': typed_node.text_content or '',
				'status': 'unreviewed',
				'url': url,
				'tags': [],
				'x': node.get('x', 0),
				'y': node.get('y', 0),
				'z': node.get('z', 0),
				'depth': typed_node.depth,
				'generalized_xpath': generalize_xpath(node_xpath) if node_xpath else '',
				'href': typed_node.href,
				'src': typed_node.src,
				'input_type': typed_node.input_type.value if hasattr(typed_node.input_type, 'value') else (str(typed_node.input_type) if typed_node.input_type else None),
				'role': typed_node.role,
				'interactive_type': typed_node.interactive_type.value if hasattr(typed_node.interactive_type, 'value') else (str(typed_node.interactive_type) if typed_node.interactive_type else None),
				'is_root': bool(node.get('is_root')),
				'label': labels_map.get(node_xpath),
			}

			ch_info = chunk_lookup.get(node_xpath)
			if ch_info:
				node_dict.update(ch_info)

			nid = xpath_to_node_id.get(node_xpath)
			if nid is not None:
				cn = colored_nodes.get(nid)
				if cn:
					node_dict['wl_hash'] = cn.color.exact_hash
					node_dict['template_hash'] = cn.color.template_hash
				tg_info = tg_lookup.get(nid)
				if tg_info:
					node_dict['template_group_id'] = tg_info['template_group_id']
					node_dict['template_tier'] = tg_info['template_tier']
					node_dict['pq_signature'] = tg_info['pq_signature']

			nodes.append(node_dict)
			if node.get('parent_xpath'):
				parent_xpath_value = node['parent_xpath']
				parent_id = f"{url}:{parent_xpath_value}"
				links.append({
					'source': node_id,
					'target': parent_id,
					'type': 'structure',
					'parent_xpath': parent_xpath_value,
				})

		emitted_ids = {n['id'] for n in nodes}
		root_id = f"{url}:/"
		for link in links:
			if link.get('type') != 'structure':
				continue
			if link['target'] in emitted_ids:
				continue
			parent_xp = link.get('parent_xpath', '')
			cur = parent_xp
			resolved = None
			while cur and cur != '/':
				cur = cur.rstrip('/').rsplit('/', 1)[0] or '/'
				candidate = f"{url}:{cur}"
				if candidate in emitted_ids:
					resolved = candidate
					break
			link['target'] = resolved or root_id

		if analytics:
			try:
				from backend.analytics.loop_closure import get_pattern_registry
				cross_edges = get_pattern_registry().get_cross_edges(min_subtree_size=3)
				for src, tgt in cross_edges:
					links.append({
						'source': f"{src['url']}:{src['xpath']}",
						'target': f"{tgt['url']}:{tgt['xpath']}",
						'type': 'cross_page',
					})
			except Exception as e:
				logger.debug(f"[Mapper] Cross‑page edge generation skipped: {e}")

		bounding_radius = flat[0].get('bounding_radius', 50) if flat else 50
		offset_x = flat[0].get('offset_x', 0) if flat else 0

		callback({
			'type': 'nodes',
			'nodes': nodes,
			'links': links,
			'boundingRadius': bounding_radius,
			'offsetX': offset_x,
			'url': url,
			'snapshot_id': snapshot_id,
			'clear_previous': True,
		})

		if is_final:
			callback({'type': 'done'})

	# ------------------------------------------------------------------
	# 6. RELEASE — free memory
	# ------------------------------------------------------------------

	def release(self, snapshot_id: str) -> None:
		self._active_doms.pop(snapshot_id, None)
		self._active_trees.pop(snapshot_id, None)
		self._active_tagged.pop(snapshot_id, None)
		self._active_layouts.pop(snapshot_id, None)
		self._active_analytics.pop(snapshot_id, None)
		self._active_chunks.pop(snapshot_id, None)
		logger.info(f"[Mapper] Released memory for snapshot {snapshot_id}")

	# ------------------------------------------------------------------
	# 6a‑delta. REAL‑TIME DELTA PROCESSING
	# ------------------------------------------------------------------

	def _init_delta_indexes(self, url: str) -> None:
		self._delta_chunk_ledger = {}
		self._delta_claimed = {}
		self._delta_pattern_chunks = {}
		# Patricia trie of generalized chunk patterns. The spec calls
		# this the "chunk pattern containment ledger" — it's how
		# instance-count rollups work across nested patterns, and how
		# up/down recursion finds chunks under a prefix.
		from backend.mapper.pattern_trie import PatternTrie
		self._pattern_trie = PatternTrie()
		# Content-distilled HTML snapshots per URL — one fragment per
		# chunk, keyed by the chunk's representative absolute xpath.
		# Reassembled with the source DOM's structure preserved so the
		# trie's generalized xpaths still navigate it cleanly after
		# the scroll completes.
		self._distilled_chunks_by_url: Dict[str, Dict[str, str]] = (
			getattr(self, '_distilled_chunks_by_url', {})
		)
		self._distilled_chunks_by_url.setdefault(url, {})
		# Set of (url, content_hash) we've already pushed to TF-IDF.
		# Stops a re-emit with identical token-bag from inflating the
		# index. Cleared per-scan because the mapper instance survives
		# multiple snapshot() calls and per-scan dedup is what the
		# spec actually wants.
		self._tfidf_seen_hashes: Set[str] = set()

	def _clear_delta_indexes(self) -> None:
		self._delta_chunk_ledger.clear()
		self._delta_claimed.clear()
		self._delta_pattern_chunks.clear()
		self._billboard_cache.clear()
		if hasattr(self, '_pattern_trie'):
			self._pattern_trie.clear()

	def _push_to_tfidf_worker(self, chunks, instances):
		"""Push verified-delta chunks into the global TF-IDF store.

		If a multiprocess `_tfidf_queue` is wired (currently never — the
		scanner doesn't expose one), forward there. Otherwise fall back to
		an in-process `gstore.add_chunks` call so the index actually
		populates in standalone scans. Without this fallback, JS-mode
		runs reported `chunks_vectorized` > 0 but `vocab_size: 0,
		doc_count: 0` because the queue path silently dropped every batch.
		"""
		from backend.services.global_tfidf_store import ChunkMeta, _tokens
		import hashlib
		metas = []
		texts = []
		seen_hashes = getattr(self, '_tfidf_seen_hashes', None)
		if seen_hashes is None:
			seen_hashes = set()
			self._tfidf_seen_hashes = seen_hashes
		for c, inst in zip(chunks, instances):
			base_text = inst.rendered_text or ""
			# Tokenize URL path nodes so a query like "softwarelibrary_msdos"
			# can hit a card whose only carrier was /details/softwarelibrary
			# _msdos_games. Without this, URL fields are stored verbatim
			# in content_fields but never enter the TF-IDF token bag,
			# leaving retrieval blind to slug-form queries.
			url_tokens: List[str] = []
			fields_obj = getattr(inst, 'fields', None) or {}
			for k, v in fields_obj.items():
				if not v:
					continue
				if "/@" not in k:
					continue
				attr = k.rsplit("/@", 1)[-1]
				if attr in ("href", "src", "data-src", "data-original",
				            "srcset", "poster", "data-image", "data-href",
				            "action", "cite"):
					url_tokens.append(_tokenize_url_path(str(v)))
			extra = " ".join(t for t in url_tokens if t)
			text = (base_text + " " + extra).strip() if extra else base_text
			# Exact-token-set dedup: hash the sorted token bag and skip
			# any chunk whose token bag we've already pushed for this
			# URL within the current scan. Catches the "same nav link
			# under five different absolute xpaths" case the spec calls
			# out as deduplication-over-exact-token-matches.
			tok_bag = tuple(sorted(set(_tokens(text))))
			if tok_bag:
				h = hashlib.blake2b(
					("\x1f".join(tok_bag)).encode("utf-8"),
					digest_size=12,
				).hexdigest()
				if h in seen_hashes:
					continue
				seen_hashes.add(h)
			metas.append(ChunkMeta(
				chunk_id=c.chunk_id,
				url=getattr(self, '_current_url', ''),
				snapshot_id=getattr(self, '_current_snapshot_id', ''),
				absolute_xpath=getattr(inst, 'absolute_xpath', ''),
				instance_idx=0,
				pattern=c.pattern,
				text_preview=text[:160],
			))
			texts.append(text)

		if not texts:
			# Whole batch was dup; nothing to push.
			return

		queue = getattr(self, '_tfidf_queue', None)
		if queue:
			queue.put({"action": "add", "texts": texts, "metas": metas})
			return

		# Direct in-process update — keeps the global TF-IDF store live so
		# the post-scan --query loop can search the chunks just produced.
		try:
			gstore = get_default_store()
			added = gstore.add_chunks(texts, metas)
			if hasattr(self, 'pipeline') and self.pipeline:
				self.pipeline.stats.vocab_size = gstore.vocab_size
				self.pipeline.stats.doc_count = gstore.doc_count
				self.pipeline._emit_log(
					"tfidf",
					f"+{added} chunks (vocab={gstore.vocab_size}, docs={gstore.doc_count})",
				)
		except Exception:
			logger.exception("[Mapper] direct TF-IDF add_chunks failed")

	@staticmethod
	def _normalize_js_event(evt: dict) -> dict:
		"""Translate the JS engine's camelCase delta payload into the
		snake_case shape the rest of the Python pipeline reads.

		The JS engine in wfh_chunk_engine.js emits chunkId/charCount/
		commutationCount/memberXpaths/contentFieldsFull/renderedText/htmlRaw.
		Every downstream consumer (audit export, billboard lookup, pipeline
		payload builders) expects snake_case. Normalising once at the boundary
		keeps every reader honest and stops audit.html from rendering null
		chunk_ids.
		"""
		members = evt.get("memberXpaths") or evt.get("member_xpaths") or []
		return {
			"type": evt.get("type"),
			"chunk_id": evt.get("chunkId") or evt.get("chunk_id"),
			"pattern": evt.get("pattern", ""),
			"member_xpaths": list(members),
			"sample_ids": list(evt.get("sampleIds") or evt.get("sample_ids") or []),
			"rendered_text": evt.get("renderedText") or evt.get("rendered_text") or "",
			"content_fields_full": (
				evt.get("contentFieldsFull")
				or evt.get("content_fields_full")
				or {}
			),
			"char_count": evt.get("charCount") or evt.get("char_count") or 0,
			"html_raw": evt.get("htmlRaw") or evt.get("html_raw") or "",
			"commutation_count": (
				evt.get("commutationCount")
				or evt.get("commutation_count")
				or 1
			),
			"representative_xpath": (
				evt.get("representative_xpath")
				or (members[0] if members else "")
			),
			"detector_tags": list(
				evt.get("detectorTags") or evt.get("detector_tags") or []
			),
		}

	@staticmethod
	def _field_attr_tags(content_fields: dict) -> Set[str]:
		"""Collect the generalised attr-tag suffixes from a chunk's fields.

		E.g. ``{"./a/@href": "...", "./img/@src": "...", "./h3/text()": "..."}``
		→ ``{"@href", "@src", "text()"}``. Used by the Patricia trie so
		each pattern node can advertise which content kinds the chunks
		under it actually carry.
		"""
		tags: Set[str] = set()
		for k in (content_fields or {}):
			# Field keys end in either ``/@name`` or ``/text()``.
			if "/@" in k:
				tags.add("@" + k.rsplit("/@", 1)[-1])
			elif k.endswith("/text()"):
				tags.add("text()")
		return tags

	def _apply_js_deltas(self, deltas: List[dict]):
		live_chunks = []
		live_instances = []
		for raw_evt in deltas:
			evt = self._normalize_js_event(raw_evt)
			etype = evt["type"]
			chunk_id = evt["chunk_id"]
			if etype == "chunk_removed":
				if chunk_id in self._delta_chunk_ledger:
					for xp in self._delta_chunk_ledger.pop(chunk_id, []):
						self._delta_claimed.pop(xp, None)
				if hasattr(self, '_pattern_trie'):
					self._pattern_trie.remove(chunk_id)
				# Drop the chunk's HTML fragment from the distilled-HTML
				# cache too so the next snapshot doesn't reassemble
				# stale subtrees that no longer exist on the page.
				url_cache = self._distilled_chunks_by_url.get(getattr(self, '_current_url', ''))
				if url_cache is not None:
					# We don't know the rep xpath here (the event only
					# has chunk_id), so let downstream cleanup happen
					# during the final reassembly pass. Cheap to defer.
					pass
				continue

			# Update ledger
			members = evt["member_xpaths"]
			self._delta_chunk_ledger[chunk_id] = set(members)
			for xp in members:
				self._delta_claimed[xp] = chunk_id
			pattern = evt["pattern"]
			# Register / update in the Patricia trie. Attr tags drive the
			# audit's "what kinds of content does this pattern carry"
			# annotation (e.g. {@href, @src, text()} for a card).
			if hasattr(self, '_pattern_trie'):
				self._pattern_trie.add(
					pattern,
					chunk_id,
					attr_tags=self._field_attr_tags(evt.get("content_fields_full") or {}),
				)
			# Cache the chunk's distilled HTML fragment for the eventual
			# whole-page reconstruction. Keying on the chunk's rep xpath
			# means the same DOM coordinate replaces its prior fragment
			# on update — no merge logic needed.
			rep_xp = evt.get("representative_xpath") or ""
			html_raw = evt.get("html_raw") or ""
			cur_url = getattr(self, '_current_url', '')
			if cur_url and rep_xp and html_raw:
				self._distilled_chunks_by_url.setdefault(cur_url, {})[rep_xp] = html_raw
			if pattern not in self._delta_pattern_chunks:
				self._delta_pattern_chunks[pattern] = []
			# Replace existing chunk with same ID
			existing = [c for c in self._delta_pattern_chunks[pattern] if c["chunk_id"] == chunk_id]
			if existing:
				idx = self._delta_pattern_chunks[pattern].index(existing[0])
				self._delta_pattern_chunks[pattern][idx] = evt
			else:
				self._delta_pattern_chunks[pattern].append(evt)

			# Build pipeline batch
			proxy = _DeltaChunkProxy(evt)
			inst = _DeltaInstanceLight(
				chunk_id=chunk_id,
				rendered_text=evt["rendered_text"],
				absolute_xpath=evt["representative_xpath"],
				instance_idx=0,
				pattern=pattern,
				fields=evt["content_fields_full"],
				html_raw=evt["html_raw"],
			)
			live_chunks.append(proxy)
			live_instances.append(inst)

			# Surface the per-chunk event to any composed on_stream consumer
			# (ConsoleStatsReporter, WebSocket clients) so the user sees
			# `++ [chunk_id]  chars=…` lines as chunks land. The pipeline's
			# fast path emits `chunks_partial` batches, but the reporter
			# listens for individual `chunk_added` / `chunk_replaced` events.
			if getattr(self, 'pipeline', None) and self.pipeline.on_stream:
				try:
					self.pipeline.on_stream({
						"type": etype if etype in ("chunk_added", "chunk_replaced") else "chunk_added",
						"snapshot_id": self._current_snapshot_id,
						"url": self._current_url,
						"chunk": evt,
					})
				except Exception:
					pass

		if live_chunks:
			try:
				self.pipeline.submit_verified_delta(_ChunkBatch(
					iter_idx=self._scan_iter,
					snapshot_id=self._current_snapshot_id,
					url=self._current_url,
					trace_id=f"{self._current_snapshot_id[:8]}-js-{self._scan_iter}",
					chunks=live_chunks,
					instances=live_instances,
					skip_fast_path=False,
				))
				self._push_to_tfidf_worker(live_chunks, live_instances)
			except Exception:
				logger.debug("[Mapper] JS delta batch submit failed")

	# ------------------------------------------------------------------
	# 6a. STREAMING‑PATH CHUNK BUILDER (no persist, no embed)
	# ------------------------------------------------------------------

	def _build_chunks_for_streaming(
		self, snapshot_id: str, url: str,
		char_budget: int = DEFAULT_CHAR_BUDGET,
	) -> Tuple[List[Chunk], List[Any]]:
		tree = self._active_trees.get(snapshot_id)
		if tree is None:
			return [], []
		dom = self._active_doms.get(snapshot_id)
		if dom is None and url in self._last_dom_for_url:
			dom = self._last_dom_for_url[url]

		xpath_map = self._active_xpath_maps.get(snapshot_id)
		if xpath_map is None:
			xpath_map = build_xpath_node_map(dom)
			self._active_xpath_maps[snapshot_id] = xpath_map

		text_provider = self._active_text_providers.get(snapshot_id)
		if text_provider is None:
			text_provider = build_text_provider_from_dom(dom, xpath_map=xpath_map)
			self._active_text_providers[snapshot_id] = text_provider

		structure_provider = self._active_structure_providers.get(snapshot_id)
		if structure_provider is None:
			structure_provider = build_structure_provider_from_dom(dom, xpath_map=xpath_map)
			self._active_structure_providers[snapshot_id] = structure_provider
		tagged = self._active_tagged.get(snapshot_id)
		all_tags = tagged.all_tags if tagged else []

		builder = ChunkBuilder(
			tree, text_provider,
			char_budget=char_budget, all_tags=all_tags,
			structure_provider=structure_provider,
		)
		chunks = builder.build(snapshot_id=snapshot_id)
		instances: List[Any] = []
		if chunks and dom is not None:
			try:
				instances = render_all_chunks(chunks, dom, xpath_map=xpath_map)
			except Exception:
				logger.exception("[Mapper] streaming render_all_chunks failed")
		return chunks, instances

	# ------------------------------------------------------------------
	# 6b. CHUNK — partition distilled DOM into SLM‑sized chunks
	# ------------------------------------------------------------------

	def chunk(self, snapshot_id: str, url: str,
			  char_budget: int = DEFAULT_CHAR_BUDGET,
			  persist: bool = True) -> Tuple[List[Chunk], List[Any]]:
		tree = self._active_trees.get(snapshot_id)
		if tree is None:
			tree = self.store.load_content_tree(snapshot_id)
		if tree is None:
			logger.warning(f"[Mapper] chunk() — no content tree for {snapshot_id}")
			return [], []

		dom = self._active_doms.get(snapshot_id)
		if dom is None and url in self._last_dom_for_url:
			dom = self._last_dom_for_url[url]

		t0 = time.time()
		xpath_map = self._active_xpath_maps.get(snapshot_id)
		if xpath_map is None:
			xpath_map = build_xpath_node_map(dom)
			self._active_xpath_maps[snapshot_id] = xpath_map

		text_provider = self._active_text_providers.get(snapshot_id)
		if text_provider is None:
			text_provider = build_text_provider_from_dom(dom, xpath_map=xpath_map)
			self._active_text_providers[snapshot_id] = text_provider

		structure_provider = self._active_structure_providers.get(snapshot_id)
		if structure_provider is None:
			structure_provider = build_structure_provider_from_dom(dom, xpath_map=xpath_map)
			self._active_structure_providers[snapshot_id] = structure_provider

		tagged = self._active_tagged.get(snapshot_id)
		all_tags = tagged.all_tags if tagged else []
		logger.info(f"[Mapper] Generating chunks with {len(all_tags)} active tags")

		builder = ChunkBuilder(
			tree, text_provider,
			char_budget=char_budget, all_tags=all_tags,
			structure_provider=structure_provider,
		)
		chunks = builder.build(snapshot_id=snapshot_id)
		logger.info(f"[Profiler] ChunkBuilder: {time.time() - t0:.4f}s ({len(chunks)} chunks, budget={char_budget})")

		self._active_chunks[snapshot_id] = chunks
		instances = []
		if persist and chunks:
			t1 = time.time()
			self.store.save_chunks(snapshot_id, url, chunks)
			logger.info(f"[Profiler] DB persist chunks: {time.time() - t1:.4f}s")

			try:
				instances = self._embed_and_persist_instances(
					snapshot_id=snapshot_id, url=url, chunks=chunks, dom=dom,
					xpath_map=xpath_map,
				)
			except Exception:
				logger.exception("[Mapper] embed+persist ChunkInstance rows failed")

		return chunks, instances

	def _persist_instance_rows_only(
		self, *, snapshot_id: str, url: str, instances: List[Any],
	) -> int:
		if not instances:
			return 0
		from backend.services.chunk_instance_persistence import (
			build_instance_rows, persist_chunk_instances,
		)
		from backend.database import get_connection
		conn = get_connection()
		rows = build_instance_rows(
			instances,
			version_id=snapshot_id, url=url, snapshot_id=snapshot_id,
			pattern_id_by_key={},
		)
		if not rows:
			return 0
		try:
			return persist_chunk_instances(conn, rows)
		except Exception:
			logger.exception("[Mapper] persist_chunk_instances failed")
			return 0

	def _embed_and_persist_instances(
		self, *, snapshot_id: str, url: str,
		chunks: List[Chunk], dom,
		xpath_map=None,
		instances: Optional[List[Any]] = None,
	) -> List[Any]:
		if not chunks:
			return []
		if instances is None and dom is None:
			return []

		from backend.services.tfidf_service import ChunkInstanceVectorizer
		from backend.services.chunk_instance_persistence import (
			build_instance_rows,
			build_page_embedding_row,
			persist_chunk_instances,
			persist_page_embedding,
		)
		from backend.database import get_connection

		t0 = time.time()
		if instances is None:
			instances = render_all_chunks(chunks, dom, xpath_map=xpath_map)
		if not instances:
			return []

		embedder = getattr(self, "_chunk_embedder", None)
		if embedder is None or not isinstance(embedder, ChunkInstanceVectorizer):
			embedder = ChunkInstanceVectorizer()
			self._chunk_embedder = embedder

		t1 = time.time()
		batch = embedder.embed_instances(instances)
		logger.info(
			"[Profiler] tfidf vectorize: %.3fs (%d unique texts, %d instances, vocab=%d, fit=%.1fms)",
			time.time() - t1, batch.unique_text_count, batch.embedded_count,
			batch.fit.vocabulary_size, batch.fit.fit_time_ms,
		)

		conn = get_connection()
		rows = build_instance_rows(
			instances,
			version_id=snapshot_id,
			url=url,
			snapshot_id=snapshot_id,
			pattern_id_by_key={},
		)
		if not rows:
			return []
		n = persist_chunk_instances(conn, rows)

		if batch.page_embedding is not None:
			try:
				page_row = build_page_embedding_row(
					version_id=snapshot_id, url=url,
					snapshot_id=snapshot_id,
					page_vector=batch.page_embedding,
					instance_count=len(rows),
				)
				persist_page_embedding(conn, page_row)
			except Exception:
				logger.exception("[Mapper] PageEmbedding persist failed (instances still saved)")

		try:
			gstore = get_default_store()
			chunk_id_to_meta = {}
			for ch in chunks:
				chunk_id_to_meta[ch.chunk_id] = ch
			texts: List[str] = []
			metas: List[ChunkMeta] = []
			for inst in instances:
				ch_dataclass = chunk_id_to_meta.get(inst.chunk_id)
				pattern = getattr(inst, "pattern", "") or (
					ch_dataclass.pattern if ch_dataclass else ""
				)
				preview = (inst.rendered_text or "")[:160]
				texts.append(inst.rendered_text or "")
				metas.append(ChunkMeta(
					chunk_id=inst.chunk_id,
					url=url,
					snapshot_id=snapshot_id,
					absolute_xpath=getattr(inst, "absolute_xpath", "") or "",
					instance_idx=int(getattr(inst, "instance_idx", 0) or 0),
					pattern=pattern,
					text_preview=preview,
				))
			added = gstore.add_chunks(texts, metas)
			gstore.save()
			logger.info(
				"[Profiler] global TF‑IDF: +%d chunks (total vocab=%d, total docs=%d)",
				added, gstore.vocab_size, gstore.doc_count,
			)
		except Exception:
			logger.exception("[Mapper] global TF‑IDF update failed")

		logger.info(
			"[Profiler] ChunkInstance persist total: %.3fs (%d row(s))",
			time.time() - t0, n,
		)
		return instances

	# ------------------------------------------------------------------
	# 6c. LIVE CHUNK DETAIL (§8.4 billboard serialization)
	# ------------------------------------------------------------------

	def get_live_chunk_detail(self, chunk_id: str) -> Optional[Dict[str, Any]]:
		cached = self._billboard_cache.get(chunk_id)
		if cached is not None:
			return cached

		# _delta_master_tree was the merged ShadowDOM-tree object used by
		# the legacy non-JS-engine path. JS-engine mode never sets it, so
		# defensively resolve it via getattr instead of a hard reference
		# — otherwise every /api/chunk_details/<id> request fails with
		# AttributeError before the JS-mode early-return below has a
		# chance to serve cached html_raw from the chunk dict itself.
		tree = getattr(self, "_delta_master_tree", None)

		target_chunk = None
		for chunks_list in self._delta_pattern_chunks.values():
			for ch in chunks_list:
				if ch.get("chunk_id") == chunk_id:
					target_chunk = ch
					break
			if target_chunk:
				break

		if target_chunk is None:
			return None

		# Stored events are normalised to snake_case at _apply_js_deltas; treat
		# the presence of either html_raw key as the JS-mode signal.
		if "html_raw" in target_chunk or "htmlRaw" in target_chunk:
			result = {
				"chunk_id": chunk_id,
				"html_raw": target_chunk.get("html_raw") or target_chunk.get("htmlRaw", ""),
				"rendered_text": target_chunk.get("rendered_text") or target_chunk.get("renderedText", ""),
				"image_urls": [],
				"content_fields": (
					target_chunk.get("content_fields_full")
					or target_chunk.get("contentFieldsFull")
					or {}
				),
			}
			self._billboard_cache[chunk_id] = result
			return result

		rep_xpath = target_chunk.get("representative_xpath", "")

		scanner = self._active_scanner
		subtree_node = None
		if scanner is not None and rep_xpath:
			subtree_node = scanner.lookup_node_by_xpath(rep_xpath)
		elif tree is not None:
			# Legacy non-JS path. Only walk a real tree object; in
			# JS-engine mode the html_raw early-return above already
			# handled the request and we don't reach here.
			subtree_node = self._find_tree_node(tree, rep_xpath)
		html_raw = ""
		rendered_text = ""
		image_urls = []
		content_fields = {}

		if subtree_node is not None:
			html_raw = self._serialize_subtree_html(subtree_node)
			rendered_text = self._extract_subtree_text(subtree_node)
			image_urls = self._extract_image_urls(subtree_node)
			meta = subtree_node.get("_meta", {})
			content_fields = meta.get("content_fields", {})

		result = {
			"chunk_id": chunk_id,
			"html_raw": html_raw,
			"rendered_text": rendered_text,
			"image_urls": image_urls,
			"content_fields": content_fields,
		}
		self._billboard_cache[chunk_id] = result
		return result

	def _invalidate_billboard_cache(self, chunk_id: str) -> None:
		self._billboard_cache.pop(chunk_id, None)

	@staticmethod
	def _build_light_content_tree_from_xpaths(xpaths: List[str]) -> Dict[str, Any]:
		"""Construct a minimal Patricia trie from a set of absolute xpaths.
		Each leaf gets an empty _content list; intermediate nodes are
		structural only.  This keeps the content-tree contract while
		3D layout and detail queries still work against known nodes.
		"""
		tree: Dict[str, Any] = {"_xpath": "/", "_content": [], "children": {}}
		for xp in xpaths:
			if not xp or xp == "/":
				continue
			parts = xp.strip("/").split("/")
			current = tree
			cumulative = ""
			for part in parts:
				tag = part.split("[")[0]
				cumulative += "/" + part
				children = current.setdefault("children", {})
				if tag not in children:
					children[tag] = {"_xpath": cumulative, "_content": [], "children": {}}
				current = children[tag]
			current["_content"].append("content")
		return tree

	@staticmethod
	def _find_tree_node(tree: dict, xpath: str) -> Optional[dict]:
		if not xpath or not tree:
			return None
		node_xpath = tree.get("_xpath") or tree.get("xpath", "")
		if node_xpath == xpath:
			return tree
		queue = list(tree.get("children", []))
		while queue:
			node = queue.pop(0)
			nxp = node.get("_xpath") or node.get("xpath", "")
			if nxp == xpath:
				return node
			queue.extend(node.get("children", []))
			sr = node.get("shadow_root")
			if sr:
				queue.extend(sr.get("children", []))
		return None

	@staticmethod
	def _serialize_subtree_html(node: dict, depth: int = 0) -> str:
		tag = node.get("tag", "div")
		attrs = node.get("_meta", {}).get("attributes", {})
		text = node.get("text", "") or ""
		children = node.get("children", [])

		skip_attrs = {"class", "style", "data-reactid", "data-testid"}
		attr_parts = []
		for k, v in attrs.items():
			if k.lower() in skip_attrs:
				continue
			attr_parts.append(f'{k}="{v}"')
		attr_str = (" " + " ".join(attr_parts)) if attr_parts else ""

		if not children and not text:
			return f"<{tag}{attr_str} />"

		inner = text
		for child in children:
			inner += DomMapper._serialize_subtree_html(child, depth + 1)

		return f"<{tag}{attr_str}>{inner}</{tag}>"

	@staticmethod
	def _extract_subtree_text(node: dict) -> str:
		parts = []
		text = node.get("text", "") or ""
		if text.strip():
			parts.append(text.strip())
		for child in node.get("children", []):
			ct = DomMapper._extract_subtree_text(child)
			if ct:
				parts.append(ct)
		return " ".join(parts)

	@staticmethod
	def _extract_image_urls(node: dict) -> List[str]:
		urls = []
		meta = node.get("_meta", {})
		attrs = meta.get("attributes", {})
		tag = node.get("tag", "").lower()
		if tag in ("img", "image") and "src" in attrs:
			urls.append(attrs["src"])
		for child in node.get("children", []):
			urls.extend(DomMapper._extract_image_urls(child))
		return urls

	# ------------------------------------------------------------------
	# 7. ANALYZE — WL coloring + template grouping on ShadowDOM
	# ------------------------------------------------------------------

	def analyze(self, snapshot_id: str, url: str) -> Optional[Dict]:
		"""Run WL structural coloring and template grouping on the active DOM.
		
		Returns a dict of distiller results keyed for FeatureRunner consumption,
		or None if the DOM is not available.
		"""
		dom = self._active_doms.get(snapshot_id)
		if dom is None:
			logger.warning(f"[Mapper] analyze() — no active DOM for {snapshot_id}")
			return None

		try:
			from backend.dom.dom_wl_miner import WLColorEngine, TemplateGrouper

			t0 = time.time()
			engine = WLColorEngine(dom)
			colored_nodes = engine.color()
			logger.info(f"[Profiler] WL coloring: {time.time() - t0:.4f}s, "
				f"{len(colored_nodes)} nodes colored")

			t1 = time.time()
			grouper = TemplateGrouper(colored_nodes, dom)
			template_groups = grouper.group()
			logger.info(f"[Profiler] Template grouping: {time.time() - t1:.4f}s, "
				f"{len(template_groups)} groups")

			# Build xpath ↔ node_id mappings for FeatureRunner adapters
			xpath_to_node_id: Dict[str, int] = {}
			xpath_lookup: Dict[int, str] = {}
			for node in dom.root.iter_all():
				node_id = getattr(node, 'node_id', None) or id(node)
				xpath = get_absolute_xpath(node)
				if xpath:
					xpath_to_node_id[xpath] = node_id
					xpath_lookup[id(node)] = xpath

			# Register WL hashes in PatternRegistry for cross-page loop closure
			from backend.analytics.loop_closure import get_pattern_registry
			registry = get_pattern_registry()
			node_hashes = {
				xpath: colored_nodes[nid].color.exact_hash
				for xpath, nid in xpath_to_node_id.items()
				if nid in colored_nodes
			}
			cross_matches = registry.register_snapshot(url, snapshot_id, node_hashes)
			if cross_matches > 0:
				logger.info(f"[Mapper] Loop closure: {cross_matches} cross-page matches for {url}")

			results = {
				'colored_nodes': colored_nodes,
				'template_groups': template_groups,
				'xpath_to_node_id': xpath_to_node_id,
				'xpath_lookup': xpath_lookup,
			}
			self._active_analytics[snapshot_id] = results
			logger.info(f"[Profiler] Total analyze phase: {time.time() - t0:.4f}s")
			return results

		except Exception as e:
			logger.error(f"[Mapper] analyze() failed: {e}", exc_info=True)
			return None

	# ------------------------------------------------------------------
	# Adaptive resumption helper (#17)
	# ------------------------------------------------------------------

	def _compute_live_content_hash(self, url: str) -> Optional[str]:
		"""Return a SHA-1 fingerprint of the live page's DOM for resumption.

		Hashes ``document.documentElement.outerHTML`` truncated to 50 KB
		plus a couple of cheap structural signals (scrollHeight, total
		element count). The 50 KB cap keeps the WebDriver round-trip
		fast while staying long enough to catch most edits — minor
		layout tweaks, advert rotations, and SPA hydration noise will
		fingerprint differently from the prior scan and rightly trigger
		a fresh pipeline; a genuinely unchanged page collides exactly.

		Returns ``None`` on any Selenium / driver error so the caller
		falls back to a normal scan rather than crashing.
		"""
		import hashlib
		if self.driver is None:
			return None
		try:
			# Single round-trip: capture the three signals together so
			# we don't pay three Selenium IPC hops.
			payload = self.driver.execute_script(
				"return {h: (document.documentElement && document.documentElement.outerHTML || '').slice(0, 50000),"
				"        sh: (document.documentElement && document.documentElement.scrollHeight) || 0,"
				"        n: document.querySelectorAll('*').length};"
			)
		except Exception as exc:
			logger.debug("[Mapper] live content hash probe failed: %s", exc)
			return None
		try:
			body = (
				(payload.get("h") or "")
				+ "|sh=" + str(payload.get("sh") or 0)
				+ "|n=" + str(payload.get("n") or 0)
				+ "|u=" + (url or "")
			)
			return hashlib.sha1(body.encode("utf-8", errors="replace")).hexdigest()[:20]
		except Exception:
			return None

	# ------------------------------------------------------------------
	# Full pipeline
	# ------------------------------------------------------------------

	def snapshot(self, url: str, max_duration: int = 60,
		pause: float = 1.0, offset_x: float = 0.0,
		on_stream: Callable = None,
		no_persist: bool = False) -> Dict[str, Any]:
		"""Run the full pipeline: scan → distill → layout → stream (full-send) → release.

		Args:
			no_persist: When True, all kuzu DB writes are skipped (TF-IDF
			            vectorisation still runs; only persistence is disabled).
			            Use when running without a database (e.g. --no-db flag).
		"""
		t_start = time.time()

		if not self.driver:
			raise RuntimeError("No WebDriver attached to mapper")

		# Adaptive resumption (#17): if this URL was scanned previously
		# AND the live page's outerHTML hash matches the stored hash,
		# the page is unchanged — skip the entire pipeline and emit a
		# cached-result frame so the GUI can re-render from existing
		# kuzu data without paying for Selenium / distill / chunk /
		# vectorize again. This is the difference between "double-click
		# scan reruns 125s of work" and "cached → instant".
		live_hash = self._compute_live_content_hash(url)
		prior_hash = self._content_hash_for_url.get(url)
		if (
			live_hash is not None
			and prior_hash is not None
			and live_hash == prior_hash
			and url in self._last_snapshot_for_url
			# Only skip if the previous scan captured a full DOM (not just JS delta)
			and self._last_dom_for_url.get(url) is not None
		):
			cached_snapshot_id = self._last_snapshot_for_url[url]
			logger.info(
				"[Mapper] adaptive resume: %s unchanged since last scan "
				"(snapshot=%s) — skipping pipeline",
				url, cached_snapshot_id,
			)
			if on_stream:
				try:
					on_stream({
						"type": "cached",
						"snapshot_id": cached_snapshot_id,
						"url": url,
						"reason": "live_html_hash_unchanged",
					})
					on_stream({
						"type": "done",
						"snapshot_id": cached_snapshot_id,
						"cached": True,
					})
				except Exception:
					logger.exception("[Mapper] cached-frame emit failed")
			return {
				"snapshot_id": cached_snapshot_id,
				"is_new": False,
				"cached": True,
				"url": url,
			}

		current_snapshot_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
		self._current_snapshot_id = current_snapshot_id
		self._current_url = url

		content_tree = {}
		content_xpaths = []
		dom = None
		last_master_tree = None

		# Initialize delta indexes for real-time chunking
		self._init_delta_indexes(url)
		scanner = ShadowDOMScanner(self.driver)
		self._active_scanner = scanner  # enables O(1) billboard lookup during scan

		self._scan_iter = 0
		_cfg = _get_pipeline_config()

		# Compose ConsoleStatsReporter around on_stream so the live counters,
		# per-chunk events, stage logs, and the optional audit.html report
		# all surface even when no WebSocket consumer is attached (standalone
		# scan.py without --ws-port). Suppressed by WFH_QUIET=1.
		on_stream, self._console_reporter = make_console_stream(on_stream)

		self.pipeline = SnapshotPipeline(on_stream=on_stream)
		if not no_persist:
			self.pipeline.set_persist_fn(
				lambda batch: self._persist_instance_rows_only(
					snapshot_id=current_snapshot_id, url=url, instances=batch.instances
				)
			)
		else:
			self.pipeline.set_persist_fn(lambda batch: 0)
		self.pipeline.start()

		for item in scanner.scan(url, max_duration=max_duration, pause=pause):
			if not hasattr(self, '_tfidf_queue') or self._tfidf_queue is None:
				self._tfidf_queue = getattr(scanner, 'tfidf_queue', None)
				if self._tfidf_queue and hasattr(self, 'pipeline') and self.pipeline and hasattr(self.pipeline, 'set_vectorize_fn'):
					self.pipeline.set_vectorize_fn(None)

			self._scan_iter += 1
			if isinstance(item, list):
				# JS delta batch (may be empty on quiet iterations)
				t_apply = time.time()
				if item:
					self._apply_js_deltas(item)
				dt_apply = time.time() - t_apply
				if hasattr(self, 'pipeline') and self.pipeline:
					# Count every iteration — empty or not — so iter_count and
					# the live stats line track real scroll progress.
					self.pipeline.note_iter(n_nodes=len(item))
					if item:
						self.pipeline._emit_log(
							"scan",
							f"iter {self._scan_iter}: applied {len(item)} JS delta(s) in {dt_apply*1000:.0f}ms",
						)
					else:
						self.pipeline._emit_log("scan", f"iter {self._scan_iter}: no deltas")
			else:
				master_tree, added_nodes, pre_chunks = item if len(item) == 3 else (item[0], item[1], [])
				last_master_tree = master_tree
				# Do NOT call _process_distill here – it will be done once at the end.

				# Existing delta handling for legacy path (if active)
				if getattr(_cfg, 'live_chunking', 'js') != "js":
					delta = getattr(scanner, 'last_delta', {})
					if '_handle_delta_events' in locals() or '_handle_delta_events' in globals():
						_handle_delta_events(delta)

		# Final distill – run ONCE after all scrolling to get the DOM / content tree
		if last_master_tree is not None:
			logger.info("[Mapper] Running final distill on complete master tree (%d scroll iters)",
						self._scan_iter)
			html = serialize_to_html(last_master_tree)
			content_tree = self.distill(current_snapshot_id, url, html=html, persist=False)
			dom = self._active_doms.get(current_snapshot_id)
			if dom:
				tagged = self._active_tagged.get(current_snapshot_id)
				if tagged:
					content_xpaths = tagged.all_content_xpaths()

		from backend.dom.shadow_html_parser import get_absolute_xpath
		def _prune_dom_to_content(root, content_xpaths_set):
			valid_prefixes = set()
			for cxp in content_xpaths_set:
				parts = cxp.split('/')
				for i in range(1, len(parts) + 1):
					valid_prefixes.add('/'.join(parts[:i]))

			def _p(node):
				node.children = [c for c in node.children if get_absolute_xpath(c) in valid_prefixes]
				if node.shadow_root:
					node.shadow_root.children = [sc for sc in node.shadow_root.children if get_absolute_xpath(sc) in valid_prefixes]
					for sc in node.shadow_root.children: _p(sc)
				for c in node.children: _p(c)
			_p(root)

		def serialize_shadow_node(node) -> str:
			if getattr(node, 'is_shadow_root', False):
				inner = "".join(serialize_shadow_node(c) for c in getattr(node, 'children', []))
				return f"<template shadowrootmode='open'>{inner}</template>"
			if node.tag == "#text":
				return node.text or ""
			if node.tag == "#comment":
				return f"<!--{node.text}-->"
			if node.tag == "#document":
				return "".join(serialize_shadow_node(c) for c in getattr(node, 'children', []))

			attrs = "".join(f' {k}="{v}"' for k,v in node.attributes.items())
			inner = ""
			if getattr(node, 'shadow_root', None):
				inner += serialize_shadow_node(node.shadow_root)
			inner += "".join(serialize_shadow_node(c) for c in getattr(node, 'children', []))

			from backend.dom.shadow_html_parser import VOID_ELEMENTS
			if node.tag in VOID_ELEMENTS:
				return f"<{node.tag}{attrs}/>"
			return f"<{node.tag}{attrs}>{inner}</{node.tag}>"

		# Save distilled source HTML and Patricia trie to DB (skipped with no_persist)
		if dom is not None:
			_prune_dom_to_content(dom.root, set(content_xpaths))
			distilled_html = serialize_shadow_node(dom.root)
			if not no_persist:
				self.store.save_snapshot(url, distilled_html, snapshot_id=current_snapshot_id)
				self.store.save_content_tree(current_snapshot_id, url, content_tree)
		else:
			logger.info("[Mapper] No full DOM captured (JS delta mode); skipping DOM save.")
			distilled_html = ""
			# Rebuild a lightweight content tree from chunk member xpaths
			all_xpaths = []
			for cid, members in self._delta_chunk_ledger.items():
				all_xpaths.extend(members)
			content_tree = DomMapper._build_light_content_tree_from_xpaths(all_xpaths)
			self._last_tree_for_url[url] = content_tree
			logger.info("[Mapper] Built light content tree with %d distinct xpaths", len(all_xpaths))

		# Persist the last DOM and content tree per URL so search/detail
		# queries work after release() clears the per-snapshot caches.
		if dom is not None:
			if current_snapshot_id in self._active_doms:
				self._last_dom_for_url[url] = self._active_doms[current_snapshot_id]
			if content_tree:
				self._last_tree_for_url[url] = content_tree
			self._last_snapshot_for_url[url] = current_snapshot_id
			if live_hash is not None:
				self._content_hash_for_url[url] = live_hash
		else:
			# For JS delta mode, keep the previous cached DOM/tree if any, but don't
			# store a new full snapshot.  Clear the live hash to force a full scan
			# next time (since we don't have a complete DOM to compare).
			self._content_hash_for_url.pop(url, None)
			logger.debug("[Mapper] Cleared live hash for %s (no full DOM captured)", url)

		# Snapshot delta state BEFORE clearing — needed for total_chunks count
		# and for the HTML report.  _clear_delta_indexes() wipes these dicts
		# in-place so we must read them here while they're still populated.
		total_chunks = len(self._delta_chunk_ledger)

		# Assemble full details for every chunk in the delta index. Each
		# chunk now also carries the forward-truncated pattern + trie
		# instance counts so the --query loop and any downstream
		# consumers see audit-equivalent info.
		from backend.mapper.pattern_trie import forward_truncate as _ft
		trie = getattr(self, '_pattern_trie', None)
		chunk_level: Dict[str, dict] = {}
		for pat_chunks in self._delta_pattern_chunks.values():
			for c in pat_chunks:
				cid = c.get("chunk_id")
				rep_xp = c.get("representative_xpath", "")
				pat = c.get("pattern", "")
				fields_full = c.get("content_fields_full") or c.get("content_fields", {})
				attr_tag_summary = sorted(self._field_attr_tags(fields_full))
				chunk_level[cid] = {
					"chunk_id": cid,
					"pattern": pat,
					"pattern_display": _ft(
						pat, 3,
						attr_tag=",".join(attr_tag_summary) if attr_tag_summary else "",
					),
					"commutation_count": (
						trie.instance_count(pat) if trie else c.get("commutation_count") or 1
					),
					"subtree_count": trie.subtree_count(pat) if trie else 1,
					"char_count": c.get("char_count"),
					"rendered_text": c.get("rendered_text", ""),
					"content_fields_full": fields_full,
					"content_fields": fields_full,  # back-compat alias
					"representative_xpath": rep_xp,
					"member_xpaths": c.get("member_xpaths", []),
					"detector_tags": c.get("detector_tags", []),
				}

		# Patricia-trie summary rows for audit + query — list of
		# (full_pattern, here, subtree, attr_tags) sorted by subtree desc.
		trie_rows = list(trie.iter_summaries()) if trie else []

		# Per-pattern detector tag map (e.g. {"<pattern>": ["search"]}).
		pattern_tags: Dict[str, List[str]] = {}
		for pat_chunks in self._delta_pattern_chunks.values():
			for c in pat_chunks:
				pat = c.get("pattern", "")
				dt = c.get("detector_tags") or []
				if dt and pat:
					existing = set(pattern_tags.get(pat, []))
					existing.update(dt)
					pattern_tags[pat] = sorted(existing)

		# ---- Export combined data for the query loop ----
		export_data = {
			"chunks": chunk_level,
			"trie_rows": trie_rows,
			"pattern_tags": pattern_tags,
			"page_url": url,
		}

		# ---- Persist content-distilled HTML to disk so future scans
		# can compare structure or replay queries without re-running
		# Selenium. One file per url, named after the URL hash.
		try:
			distilled_chunks = self._distilled_chunks_by_url.get(url) or {}
			if distilled_chunks:
				import hashlib as _hl
				snap_dir = _os.path.join(
					_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
					"..", "snapshots", "distilled_html",
				)
				_os.makedirs(snap_dir, exist_ok=True)
				name = _hl.md5(url.encode("utf-8")).hexdigest()[:16] + ".html"
				out_path = _os.path.normpath(_os.path.join(snap_dir, name))
				rebuilt = _reassemble_distilled_html(url, distilled_chunks)
				with open(out_path, "w", encoding="utf-8") as _fp:
					_fp.write(rebuilt)
				logger.info(
					"[Mapper] Distilled HTML saved: %s (%d chunk fragments)",
					out_path, len(distilled_chunks),
				)
		except Exception:
			logger.exception("[Mapper] distilled HTML save failed")

		# Hand the final chunk state to the console reporter BEFORE clearing —
		# _clear_delta_indexes() empties the dicts in-place, so the reporter
		# needs a shallow copy of the per-pattern lists to render audit.html
		# in its 'done' handler.
		if getattr(self, '_console_reporter', None) is not None:
			try:
				self._console_reporter.attach_pattern_chunks(
					{k: list(v) for k, v in self._delta_pattern_chunks.items()},
					dict(self._billboard_cache),
					trie_rows=trie_rows,
					pattern_tags=pattern_tags,
					page_url=url,
				)
			except Exception:
				logger.exception("[Mapper] attach_pattern_chunks failed")

		# Clear delta indexes and scanner reference now that we've snapshotted
		# everything we need from them.
		self._clear_delta_indexes()
		self._active_scanner = None

		self._dedup_stats.log_final_summary()

		if hasattr(self, 'pipeline') and self.pipeline:
			self.pipeline.finish()
			self.pipeline = None

		# Ensure the global TF-IDF index is persisted to disk now
		# that all chunks have been vectorized. The per-batch save
		# inside _vectorize_batch is debounced to 5s intervals, so
		# the tail-end of the scan may have in-memory-only rows.
		try:
			get_default_store().save()
		except Exception:
			logger.exception("[Mapper] final gstore.save() failed")

		if on_stream:
			on_stream({
			'type': 'done',
			'snapshot_id': current_snapshot_id,
			'chunk_count': total_chunks,
		})

		self.release(current_snapshot_id)
		logger.info(
			f"[Mapper] Pipeline complete: {total_chunks} chunks streamed, "
		)
		logger.info(f"[Profiler] TOTAL SNAPSHOT PIPELINE: {time.time() - t_start:.4f}s")
		return {
			'snapshot_id': current_snapshot_id,
			'is_new': True,
			'node_count': count_content_nodes(content_tree) if content_tree else 0,
			'bounding_radius': 50.0,
			'url': url,
			'chunk_count': total_chunks,
			'dom': self._last_dom_for_url.get(url),
			'chunk_details': export_data,
		}

	# ------------------------------------------------------------------
	# Node detail lookup (for knowledge panel)
	# ------------------------------------------------------------------

	def get_node_detail(self, url: str, xpath: str,
		snapshot_id: str = None) -> Dict[str, Any]:
		"""
		Get full HTML attributes and content for a specific xpath node.
		
		Loads the DOM from disk, navigates to the xpath, and returns
		the node's tag, attributes, text, and label status.
		"""
		# Try active DOM first, then per-URL cache, then disk
		dom = None
		if snapshot_id and snapshot_id in self._active_doms:
			dom = self._active_doms[snapshot_id]

		if dom is None and url in self._last_dom_for_url:
			dom = self._last_dom_for_url[url]

		if dom is None and snapshot_id:
			html = self.store.load_snapshot_html(snapshot_id)
			if html:
				dom = ShadowDOM(html)

		if dom is None:
			# Try loading the latest snapshot for this URL
			snapshots = self.store.get_snapshots_for_url(url)
			if snapshots:
				html = self.store.load_snapshot_html(snapshots[0]['snapshot_id'])
				if html:
					dom = ShadowDOM(html)

		if dom is None:
			return {
				'xpath': xpath, 'tag': '', 'attributes': {},
				'text': '', 'html': '', 'label': None,
				'categories': [], 'generalized_xpath': generalize_xpath(xpath),
			}

		# Navigate to xpath
		nodes = dom.xpath(xpath)
		if not nodes:
			return {
				'xpath': xpath, 'tag': '', 'attributes': {},
				'text': 'Node not found in DOM', 'html': '',
				'label': None, 'categories': [],
				'generalized_xpath': generalize_xpath(xpath),
			}

		node = nodes[0]
		label = self.labels.get_label_for_xpath(url, xpath)

		# Get content categories from the content tree
		categories = []
		if snapshot_id:
			tree = self._active_trees.get(snapshot_id)
			if tree is None:
				tree = self.store.load_content_tree(snapshot_id)
			if tree:
				categories = self._find_categories_in_tree(tree, xpath)

		return {
			'xpath': xpath,
			'tag': node.tag,
			'attributes': node.get_all_attrs(),
			'text': node.get_text(recursive=True, separator=' ')[:500],
			'html': node.to_html(indent=2)[:2000],
			'label': label,
			'categories': categories,
			'generalized_xpath': generalize_xpath(xpath),
		}

	# ------------------------------------------------------------------
	# DOM text search (for retrieval panel)
	# ------------------------------------------------------------------

	def search_dom_text(self, url: str, query: str,
		snapshot_id: str = None,
		limit: int = 50) -> List[Dict[str, Any]]:
		"""
		Search across all content nodes' text/innerHTML for a substring match.
		
		Returns a ranked list of matching nodes with snippet previews,
		sorted by relevance (exact match > case-insensitive > partial).
		Each result includes the node ID, xpath, tag, snippet, and categories
		so the frontend can render result cards and fly-to on click.
		"""
		# Resolve DOM — try active per-snapshot, then per-URL cache, then disk
		dom = None
		if snapshot_id and snapshot_id in self._active_doms:
			dom = self._active_doms[snapshot_id]

		if dom is None and url in self._last_dom_for_url:
			dom = self._last_dom_for_url[url]
			if not snapshot_id:
				snapshot_id = self._last_snapshot_for_url.get(url)

		if dom is None and snapshot_id:
			html = self.store.load_snapshot_html(snapshot_id)
			if html:
				dom = ShadowDOM(html)

		if dom is None:
			snapshots = self.store.get_snapshots_for_url(url)
			if snapshots:
				sid = snapshots[0]['snapshot_id']
				html = self.store.load_snapshot_html(sid)
				if html:
					dom = ShadowDOM(html)
					if not snapshot_id:
						snapshot_id = sid

		if dom is None:
			return []

		# Get the content tree so we know which xpaths are content-bearing
		content_xpaths: Set[str] = set()
		tree = self._active_trees.get(snapshot_id) if snapshot_id else None
		if tree is None and url in self._last_tree_for_url:
			tree = self._last_tree_for_url[url]
		if tree is None and snapshot_id:
			tree = self.store.load_content_tree(snapshot_id)
		if tree:
			content_xpaths = set(self._collect_all_xpaths(tree))

		query_lower = query.lower()
		results = []

		for node in dom.iter_all():
			try:
				xpath = get_absolute_xpath(node)
				if not xpath:
					continue

				# Search across both text content and innerHTML
				text = node.get_text(recursive=True, separator=" ").strip()
				try:
					inner_html = node.to_html(indent=0)[:2000]
				except Exception:
					inner_html = text

				# Check for match in text or innerHTML
				text_lower = text.lower()
				html_lower = inner_html.lower()

				if query_lower not in text_lower and query_lower not in html_lower:
					continue

				# Compute relevance score
				score = 0.0
				snippet = ''

				# Exact case match in text = highest
				if query in text:
					score = 1.0
					snippet = self._extract_snippet(text, query, context_chars=80)
				elif query_lower in text_lower:
					score = 0.8
					snippet = self._extract_snippet(text, query, context_chars=80,
						case_insensitive=True)
				elif query in inner_html:
					score = 0.5
					snippet = self._extract_snippet(inner_html, query, context_chars=80)
				else:
					score = 0.3
					snippet = self._extract_snippet(inner_html, query, context_chars=80,
						case_insensitive=True)

				# Boost content-bearing nodes
				is_content = xpath in content_xpaths
				if is_content:
					score += 0.1

				# Get categories if available
				categories = []
				if tree and is_content:
					categories = self._find_categories_in_tree(tree, xpath)

				node_id = f"{url}:{xpath}"
				tag = node.tag or ''
				attrs = {}
				try:
					attrs = node.get_all_attrs()
				except Exception:
					pass

				display_name = tag
				if 'id' in attrs:
					display_name = f"{tag}#{attrs['id']}"

				results.append({
					'id': node_id,
					'xpath': xpath,
					'tag': tag,
					'name': display_name,
					'text': text[:200],
					'snippet': snippet,
					'score': min(score, 1.0),
					'categories': categories,
					'is_content': is_content,
					'url': url,
					'depth': self._xpath_depth(xpath),
					'generalized_xpath': generalize_xpath(xpath),
				})
			except Exception:
				continue

		# Sort by score descending, then by depth ascending
		results.sort(key=lambda r: (-r['score'], r['depth']))
		return results[:limit]

	@staticmethod
	def _extract_snippet(text: str, query: str, context_chars: int = 80,
		case_insensitive: bool = False) -> str:
		"""Extract a snippet around the first occurrence of query in text."""
		search_text = text.lower() if case_insensitive else text
		search_query = query.lower() if case_insensitive else query
		idx = search_text.find(search_query)
		if idx == -1:
			return text[:context_chars * 2]
		start = max(0, idx - context_chars)
		end = min(len(text), idx + len(query) + context_chars)
		snippet = text[start:end]
		if start > 0:
			snippet = '…' + snippet
		if end < len(text):
			snippet = snippet + '…'
		return snippet

	def _collect_all_xpaths(self, tree: Dict[str, Any]) -> List[str]:
		"""Collect all _xpath values from a content tree."""
		xpaths = []
		for key, subtree in tree.items():
			if key.startswith('_'):
				continue
			if isinstance(subtree, dict):
				xp = subtree.get('_xpath', key)
				xpaths.append(xp)
				xpaths.extend(self._collect_all_xpaths(subtree))
		return xpaths

	# ------------------------------------------------------------------
	# LCA + Commutation queries (for retrieval panel highlighting)
	# ------------------------------------------------------------------

	def get_lca_subtree(self, url: str, label: str,
		snapshot_id: str = None) -> Dict[str, Any]:
		"""
		Compute the LCA subtree for a label group and return
		all content xpaths under the LCA for 3D highlighting.
		"""
		from backend.mapper.label_engine import compute_lca, find_lca_subtree_xpaths

		lca_info = self.labels.get_lca_for_label(url, label)
		lca_xpath = lca_info.get('lca_xpath', '/')
		member_xpaths = lca_info.get('member_xpaths', [])

		# Load content tree to find all nodes in the LCA subtree
		tree = self._active_trees.get(snapshot_id) if snapshot_id else None
		if tree is None and url in self._last_tree_for_url:
			tree = self._last_tree_for_url[url]
		if tree is None and snapshot_id:
			tree = self.store.load_content_tree(snapshot_id)
		if tree is None:
			snapshots = self.store.get_snapshots_for_url(url)
			if snapshots:
				tree = self.store.load_content_tree(snapshots[0]['snapshot_id'])

		subtree_xpaths = []
		if tree:
			subtree_xpaths = find_lca_subtree_xpaths(tree, member_xpaths)

		return {
			'label': label,
			'lca_xpath': lca_xpath,
			'member_xpaths': member_xpaths,
			'subtree_xpaths': subtree_xpaths,
			'member_count': len(member_xpaths),
		}

	def get_commutation_matches(self, url: str, xpath: str,
		snapshot_id: str = None) -> Dict[str, Any]:
		"""
		Find all content nodes matching the same generalized xpath pattern.
		Used for lateral commutation highlighting across the Patricia trie.
		"""
		pattern = generalize_xpath(xpath)

		# Load content tree
		tree = self._active_trees.get(snapshot_id) if snapshot_id else None
		if tree is None and url in self._last_tree_for_url:
			tree = self._last_tree_for_url[url]
		if tree is None and snapshot_id:
			tree = self.store.load_content_tree(snapshot_id)
		if tree is None:
			snapshots = self.store.get_snapshots_for_url(url)
			if snapshots:
				tree = self.store.load_content_tree(snapshots[0]['snapshot_id'])

		matching_xpaths = []
		if tree:
			all_xpaths = self._collect_all_xpaths(tree)
			matching_xpaths = [xp for xp in all_xpaths
				if generalize_xpath(xp) == pattern]

		return {
			'source_xpath': xpath,
			'pattern': pattern,
			'matching_xpaths': matching_xpaths,
			'match_count': len(matching_xpaths),
		}

	def get_subgroup_commutation_matches(self, url: str, xpath: str,
		snapshot_id: str = None) -> Dict[str, Any]:
		"""
		Subgroup commutation — commute only across structures that share
		the SAME SET of descendant generalized xpath patterns, restricted
		to subtrees belonging to a "connected group" (a labeled LCA with
		at least two labeled member nodes).
		
		Preconditions enforced:
		  1. ≥2 labeled nodes exist for the URL.
		  2. The LCA xpath of those labels is itself labeled.
		
		Given a source xpath in such a group, we scan the full content
		tree and return every xpath whose descendant pattern-set matches
		the source's descendant pattern-set (structural isomorphism at
		the generalized-xpath level).
		"""
		# 1) Load the content tree for this URL / snapshot.
		tree = self._active_trees.get(snapshot_id) if snapshot_id else None
		if tree is None and url in self._last_tree_for_url:
			tree = self._last_tree_for_url[url]
		if tree is None and snapshot_id:
			tree = self.store.load_content_tree(snapshot_id)
		if tree is None:
			snapshots = self.store.get_snapshots_for_url(url)
			if snapshots:
				tree = self.store.load_content_tree(snapshots[0]['snapshot_id'])
		if tree is None:
			return {
				'source_xpath': xpath, 'matching_xpaths': [],
				'match_count': 0, 'reason': 'no_tree',
			}

		# 2) Find at least one "connected group": ≥2 labeled members
		#    whose LCA xpath is also labeled.
		all_labels = self.labels.get_labels_for_url(url)
		from collections import defaultdict
		by_label = defaultdict(list)
		for row in all_labels:
			by_label[row['label']].append(row['xpath'])
		labeled_xpaths = {row['xpath'] for row in all_labels}

		from backend.mapper.label_engine import compute_lca
		valid_groups = []
		for label_name, member_xpaths in by_label.items():
			if len(member_xpaths) < 2:
				continue
			lca_xp = compute_lca(member_xpaths)
			if lca_xp in labeled_xpaths:
				valid_groups.append({
					'label': label_name,
					'lca_xpath': lca_xp,
					'members': member_xpaths,
				})

		if not valid_groups:
			return {
				'source_xpath': xpath, 'matching_xpaths': [],
				'match_count': 0, 'reason': 'no_labeled_lca_group',
			}

		# 3) Compute reference pattern set from the source xpath subtree.
		ref_patterns = self._pattern_set_under_xpath(tree, xpath)
		if not ref_patterns:
			return {
				'source_xpath': xpath, 'matching_xpaths': [],
				'match_count': 0, 'reason': 'empty_source_subtree',
			}

		# 4) Build candidate xpath pool: every member xpath of every valid
		#    connected group. Source xpath is always a candidate too so the
		#    caller can visualize its own group membership.
		candidates: Set[str] = set()
		for g in valid_groups:
			candidates.update(g['members'])
			candidates.add(g['lca_xpath'])
		candidates.add(xpath)

		# 5) Compare descendant pattern-sets and return isomorphic matches.
		matching_xpaths = []
		for cand in candidates:
			if self._pattern_set_under_xpath(tree, cand) == ref_patterns:
				matching_xpaths.append(cand)

		return {
			'source_xpath': xpath,
			'pattern_set': sorted(ref_patterns),
			'matching_xpaths': matching_xpaths,
			'match_count': len(matching_xpaths),
			'groups': [
				{'label': g['label'], 'lca_xpath': g['lca_xpath'],
					'member_count': len(g['members'])}
				for g in valid_groups
			],
		}

	def _pattern_set_under_xpath(self, tree: Dict[str, Any],
		xpath: str) -> frozenset:
		"""
		Return the frozenset of *relative* generalized xpath patterns
		descending from ``xpath`` within ``tree``. Relative means each
		descendant's generalized xpath is stripped of the source's own
		generalized prefix, so two structurally identical subtrees at
		different absolute positions compare equal.
		"""
		subtree = self._find_subtree_by_xpath(tree, xpath)
		if subtree is None:
			return frozenset()
		source_pattern = generalize_xpath(xpath)
		prefix = source_pattern.rstrip('/')
		patterns: Set[str] = set()
		self._walk_generalized_patterns(subtree, patterns)
		# Strip the source prefix so comparisons are position-independent.
		rel = set()
		for p in patterns:
			if prefix and p.startswith(prefix):
				tail = p[len(prefix):]
				rel.add(tail if tail else '/')
			else:
				rel.add(p)
		return frozenset(rel)

	def _find_subtree_by_xpath(self, tree: Dict[str, Any],
		target_xpath: str) -> Optional[Dict[str, Any]]:
		"""Walk the content tree to find the subtree dict whose _xpath matches."""
		if tree.get('_xpath') == target_xpath:
			return tree
		for key, subtree in tree.items():
			if key.startswith('_') or not isinstance(subtree, dict):
				continue
			node_xpath = subtree.get('_xpath', key)
			if node_xpath == target_xpath:
				return subtree
			found = self._find_subtree_by_xpath(subtree, target_xpath)
			if found is not None:
				return found
		return None

	def _walk_generalized_patterns(self, subtree: Dict[str, Any],
		patterns: Set[str]) -> None:
		"""Collect generalized xpaths of every descendant of ``subtree``."""
		for key, child in subtree.items():
			if key.startswith('_') or not isinstance(child, dict):
				continue
			child_xpath = child.get('_xpath', key)
			patterns.add(generalize_xpath(child_xpath))
			self._walk_generalized_patterns(child, patterns)

	def _find_categories_in_tree(self, tree: Dict[str, Any],
		target_xpath: str) -> List[str]:
		"""Find content categories for a specific xpath in the content tree."""
		for key, subtree in tree.items():
			if key.startswith('_'):
				continue
			if not isinstance(subtree, dict):
				continue
			node_xpath = subtree.get('_xpath', key)
			if node_xpath == target_xpath:
				return subtree.get('_content', [])
			# Recurse
			found = self._find_categories_in_tree(subtree, target_xpath)
			if found:
				return found
		return []

	# ------------------------------------------------------------------
	# Map queries
	# ------------------------------------------------------------------

	def get_registered_urls(self) -> List[Dict[str, Any]]:
		"""Return all URLs with registered snapshots."""
		return self.store.get_all_registered_urls()

	def get_snapshots(self, url: str) -> List[Dict[str, Any]]:
		"""Return all snapshots for a URL."""
		return self.store.get_snapshots_for_url(url)

	def load_snapshot(self, snapshot_id: str, url: str,
		offset_x: float = 0.0) -> List[Dict[str, Any]]:
		"""
		Load a snapshot from DB and compute its layout.
		Consumer-driven loading (GUI requests a specific snapshot).
		"""
		tree = self.store.load_content_tree(snapshot_id)
		if tree is None:
			# Need to re-distill from HTML
			html = self.store.load_snapshot_html(snapshot_id)
			if html is None:
				return []
			tree = self.distill(snapshot_id, url, html=html)

		self._active_trees[snapshot_id] = tree
		flat = self.layout(snapshot_id, offset_x=offset_x)
		return flat

	def rebuild_snapshot_payload(self, snapshot_id: str, url: str,
		offset_x: float = 0.0) -> Dict[str, Any]:
		"""
		Restore the full GUI payload for a previously persisted snapshot.
		
		Loads the content tree from Kuzu, re-runs layout, replays
		stream() into a buffer, and fetches persisted chunks. Used by the
		/api/map/restore endpoint so scans survive page refreshes without
		re-running the browser scanner.
		"""
		self.load_snapshot(snapshot_id, url, offset_x=offset_x)

		captured: List[Dict[str, Any]] = []

		def _sink(payload: Dict[str, Any]) -> None:
			captured.append(payload)

		self.stream(snapshot_id, url, _sink, is_final=False)

		# Collapse all streamed node/link batches into one payload.
		nodes: List[Dict[str, Any]] = []
		links: List[Dict[str, Any]] = []
		bounding_radius = 50
		for p in captured:
			if p.get('type') == 'nodes':
				nodes.extend(p.get('nodes', []))
				links.extend(p.get('links', []))
				bounding_radius = p.get('boundingRadius', bounding_radius)

		chunks = self.get_chunks(snapshot_id)

		# Fetch instances from DB to restore embedded projection payloads
		instances = []
		try:
			from backend.services.chunk_instance_persistence import load_instances_by_url
			from backend.database import get_connection
			import json
			conn = get_connection()
			rows = load_instances_by_url(conn, url)
			for r in rows:
				if r.snapshot_id == snapshot_id:
					fields = json.loads(r.fields_json) if r.fields_json else {}
					image_url = None
					link_url = None
					for k, v_list in fields.items():
						if '/@src' in k or '/@data-src' in k or '/@data-original' in k or '/@poster' in k:
							if v_list and not image_url:
								image_url = str(v_list[0])
						elif '/@href' in k:
							for val in v_list:
								val_str = str(val).lower()
								if any(val_str.split('?')[0].endswith(ext) for ext in ('.jpg','.png','.jpeg','.gif','.webp','.svg')):
									if not image_url:
										image_url = str(val)
								else:
									if not link_url:
										link_url = str(val)

					instances.append({
						"chunk_id": r.chunk_id,
						"instance_id": r.instance_id,
						"pattern": r.pattern_id,
						"absolute_xpath": r.absolute_xpath,
						"rendered_text": r.rendered_text,
						"html_raw": r.html_raw,
						"fields": fields,
						"embedding": r.embedding,
						"image_url": image_url,
						"link_url": link_url
					})
		except Exception as e:
			logger.error(f"[Mapper] Failed to load instances for restore: {e}")

		# Release the in-memory copy so we don't accumulate snapshots on
		# repeated restore calls.
		self.release(snapshot_id)

		return {
			'snapshot_id': snapshot_id,
			'url': url,
			'nodes': nodes,
			'links': links,
			'boundingRadius': bounding_radius,
			'offsetX': offset_x,
			'chunks': chunks,
			'chunk_instances': instances,
		}

	def restore_all(self) -> List[Dict[str, Any]]:
		"""
		Restore the latest persisted snapshot for every registered URL.
		
		Returns a list of payloads (same shape as rebuild_snapshot_payload)
		with offsetX assigned so the snapshots render side-by-side like a
		fresh multi-snapshot scan would.
		"""
		results: List[Dict[str, Any]] = []
		offset_x = 0.0
		for entry in self.get_registered_urls():
			url = entry.get('url')
			if not url:
				continue
			snaps = self.get_snapshots(url)
			if not snaps:
				continue
			latest = snaps[0]['snapshot_id']
			try:
				payload = self.rebuild_snapshot_payload(latest, url,
					offset_x=offset_x)
			except Exception as e:
				logger.error(f"[Mapper] restore failed for {url}: {e}",
					exc_info=True)
				continue
			br = payload.get('boundingRadius') or 50
			offset_x += br * 2.5
			results.append(payload)
		return results

	# ------------------------------------------------------------------
	# Internal: tree structure conversions
	# ------------------------------------------------------------------

	def _tree_to_layout_struct(self, tree: Dict[str, Any],
		depth: int = 0) -> Dict[str, Any]:
		"""
		Convert a collapsed content tree to the nested dict format
		expected by LayoutGenerator.apply_radial_tree_layout().
		
		Used as fallback when full layout tree is not available.
		"""
		children = []
		for key, subtree in tree.items():
			if key.startswith('_'):
				continue
			if not isinstance(subtree, dict):
				continue

			# Extract the tag from the xpath key
			tag = self._tag_from_xpath_key(key)
			child = {
				'tagName': tag,
				'nodeType': 1,
				'_xpath': subtree.get('_xpath', key),
				'_categories': subtree.get('_content', []),
				'children': [],
			}

			# Recurse into subtree children
			sub_children = self._tree_to_layout_struct(subtree, depth + 1)
			child['children'] = sub_children.get('children', [])

			children.append(child)

		return {
			'tagName': 'root',
			'nodeType': 1,
			'children': children,
			'_xpath': tree.get('_xpath', '/'),
			'_categories': tree.get('_content', []),
		}

	def _prune_contentless_branches(self, node: dict) -> None:
		"""Remove intermediate nodes that carry no content.
		
		A node is pruned when it has:
		  - No ``_categories`` (i.e. no distilled content)
		  - No text content
		  - At least one child **or** no children and no content (lone empty leaf)
		
		When a branch node is pruned its children are re-parented to the
		branch's parent, preserving tree connectivity while collapsing
		depth levels that would otherwise render as empty spheres.
		
		The root node is never pruned.
		"""
		children = node.get('children', [])

		# Recurse first (bottom-up) so that deeper empty nodes are pruned
		# before we evaluate their parents.
		for child in children:
			self._prune_contentless_branches(child)

		# Now rebuild the children list, splicing out contentless branches
		new_children: list = []
		for child in children:
			categories = child.get('_categories', [])
			text = (child.get('_text', '') or '').strip()
			grandchildren = child.get('children', [])

			is_contentless = not categories and not text

			if is_contentless and len(grandchildren) >= 2:
				# Multi-child branch: keep as a structural grouping node so
				# chunk roots (which are typically contentless parents of
				# several content leaves) reach the frontend. Without this
				# the post-scan chunking step identifies card roots that
				# were already collapsed, so card-fold finds nothing to hide.
				new_children.append(child)
			elif is_contentless and len(grandchildren) == 1:
				# Single-child passthrough: re-parent the lone grandchild.
				new_children.extend(grandchildren)
			elif is_contentless and not grandchildren:
				# Empty leaf with no content — drop entirely
				continue
			else:
				new_children.append(child)

		node['children'] = new_children

	def _tag_from_xpath_key(self, key: str) -> str:
		"""Extract the last tag name from a collapsed xpath key.
		
		'/div[2]/ul/li[3]' → 'li'
		'/main/article' → 'article'
		"""
		parts = key.rstrip('/').split('/')
		for part in reversed(parts):
			if part and not part.startswith('_'):
				# Strip index
				tag = part.split('[')[0]
				if tag:
					return tag
		return 'div'

	def _shift_layout(self, node: dict, dx: float) -> None:
		"""Apply X offset to all layout coordinates in a tree."""
		node['layout_x'] = node.get('layout_x', 0.0) + dx
		for c in node.get('children', []):
			self._shift_layout(c, dx)

	@staticmethod
	def _xpath_depth(xpath: str) -> int:
		"""Derive DOM depth from an absolute xpath by counting segments."""
		if not xpath or xpath == '/':
			return 0
		return len([s for s in xpath.strip('/').split('/') if s])

	def _flatten_layout(self, node: dict, offset_x: float,
		bounding_radius: float,
		parent_xpath: str = '',
		results: List[Dict] = None) -> List[Dict]:
		"""Flatten a layout tree into a list of nodes with server-computed
		radial-tree coordinates.
		"""
		if results is None:
			results = []

		xpath = node.get('_xpath', node.get('xpath', '/'))
		tag = node.get('tagName', node.get('tag', ''))
		categories = node.get('_categories', [])
		attributes = node.get('_attributes', {})
		text = node.get('_text', '')

		# Derive depth from the ORIGINAL xpath, not pruned tree position.
		depth = self._xpath_depth(xpath)

		# Server-computed radial-tree coordinates (with X offset)
		lx = node.get('layout_x', 0.0)
		ly = node.get('layout_y', 0.0)
		lz = node.get('layout_z', 0.0)

		# Emit every node, including the synthetic root.  Without the root
		# node the first-level subtrees have nothing to link back to and
		# appear as disconnected clouds.  The root is marked with is_root
		# so the client can style it (smaller, inert, non-clickable).
		is_root = (xpath == '/' or not xpath)
		results.append({
			'xpath': xpath or '/',
			'tag': tag or 'root',
			'categories': categories,
			'attributes': attributes,
			'text': text,
			'depth': depth,
			'parent_xpath': parent_xpath,
			'bounding_radius': bounding_radius,
			'offset_x': offset_x,
			'x': lx + offset_x,
			'y': ly,
			'z': lz,
			'is_root': is_root,
		})

		for child in node.get('children', []):
			# Every child links back to its immediate parent — including
			# the synthetic root — so every subtree is anchored.
			self._flatten_layout(child, offset_x, bounding_radius,
				parent_xpath=(xpath or '/'),
				results=results)

		return results
