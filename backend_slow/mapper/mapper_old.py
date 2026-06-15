"""
mapper.py — SLAM-inspired DOM lifecycle orchestrator.

Pipeline:  scan → distill → layout → stream → release

The mapper coordinates between:
  - Selenium WebDriver (live browser)
  - dom_distiller scanner (pure scan + merge-tree dedup)
  - dom_distiller ShadowDOM parser (parse HTML → object model)
  - dom_distiller ContentTagger (extract content xpaths + categories)
  - SnapshotStore (persist HTML files + DB records)
  - LabelEngine (labels, commutation, LCA, structure tags)
  - LayoutGenerator (3D radial-tree coordinates from tree structure)
  - GUI WebSocket stream (push full node sets to frontend)

Key design: the layout tree is built from the Patricia trie of content-bearing
nodes only, with content categories attached as metadata. Edges in the 3D GUI
follow the Patricia trie parent-child structure.
"""

from __future__ import annotations

import logging
import time
import uuid
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
)
from backend.mapper.chunk_render import render_all_chunks
from backend.mapper.chunk_absorber import ChunkAbsorber, AbsorbEvent
from backend.ontology.layout_generator import LayoutGenerator
from backend.ontology.type_handlers import TypeHandlerRegistry
from backend.ontology.interactive_ranker import InteractiveRanker

logger = logging.getLogger(__name__)


class DomMapper:
	"""
	Central orchestrator for the DOM scan/map/render pipeline.
	
	Lifecycle per snapshot (via snapshot()):
	  1. scan()     — extract DOM from live browser via Selenium
	  2. distill()  — parse HTML → ShadowDOM → content tags → Patricia trie
	  3. layout()   — compute deterministic radial-tree 3D coordinates
	  4. stream()   — push full node set to GUI via WebSocket callback
	  5. release()  — free DOM object from memory
	
	Optional standalone methods:
	  - register()  — save HTML to disk, register in DB (merge-conscious)
	  - analyze()   — WL coloring + template grouping (enriches stream payload)
	
	The mapper tracks all registered URLs and their snapshots,
	acting as the "map" in the SLAM analogy.
	"""

	def __init__(self, driver=None):
		self.driver = driver
		self.store = SnapshotStore()
		self.labels = LabelEngine()

		# In-memory cache (released after streaming)
		self._active_doms: Dict[str, ShadowDOM] = {} # snapshot_id → ShadowDOM
		self._active_trees: Dict[str, Dict] = {} # snapshot_id → content tree (for DB)
		self._active_tagged: Dict[str, TaggedContent] = {} # snapshot_id → tagged content
		self._active_layouts: Dict[str, List[Dict]] = {} # snapshot_id → flat nodes with coords
		self._active_analytics: Dict[str, Dict] = {} # snapshot_id → distiller results
		self._active_chunks: Dict[str, List[Chunk]] = {} # snapshot_id → post-scan chunks
		# (Delta streaming removed — always full-send)

		# Persistent per-URL cache for search — survives release()
		self._last_dom_for_url: Dict[str, ShadowDOM] = {} # url → most recent ShadowDOM
		self._last_tree_for_url: Dict[str, Dict] = {} # url → most recent content tree
		self._last_snapshot_for_url: Dict[str, str] = {} # url → most recent snapshot_id

	# ------------------------------------------------------------------
	# 1. SCAN — extract DOM from live browser
	# ------------------------------------------------------------------

	def scan(self, url: str, max_duration: int = 60, pause: float = 1.0) -> Any:
		"""
		Scan a URL and return the full merged HTML string.
		"""
		if not self.driver:
			raise RuntimeError("No WebDriver attached to mapper")

		scanner = ShadowDOMScanner(self.driver)
		return scanner.scan(url, max_duration=max_duration, pause=pause)

	# ------------------------------------------------------------------
	# 2. REGISTER — save to DB (merge-conscious)
	# ------------------------------------------------------------------

	def register(self, url: str, html: str,
		snapshot_id: str = None) -> Tuple[str, bool]:
		"""
		Register a scanned DOM snapshot.
		
		Saves HTML to disk, creates DB records. If the HTML hash matches
		the latest snapshot for this URL, returns the existing ID.
		
		Returns:
		    (snapshot_id, is_new)
		"""
		sid, is_new = self.store.save_snapshot(url, html, snapshot_id)
		logger.info(f"[Mapper] Registered snapshot {sid} "
			f"(new={is_new}) for {url}")
		return sid, is_new

	# ------------------------------------------------------------------
	# 3. DISTILL — parse → tag → build FULL DOM tree
	# ------------------------------------------------------------------

	def distill(self, snapshot_id: str, url: str,
		html: str = None, persist: bool = True) -> Dict[str, Any]:
		"""
		Parse HTML into ShadowDOM, extract content, build distilled DOM tree.
		
		If html is not provided, loads from disk via snapshot_id.
		
		"""
		# Load HTML if not provided
		if html is None:
			t0 = time.time()
			html = self.store.load_snapshot_html(snapshot_id)
			if html is None:
				raise ValueError(f"No HTML found for snapshot {snapshot_id}")
			logger.info(f"[Profiler] load_snapshot_html: {time.time() - t0:.4f}s")

		# Parse into ShadowDOM object
		logger.info(f"[Mapper] Parsing {len(html)} bytes into ShadowDOM...")
		t1 = time.time()
		dom = ShadowDOM(html)
		self._active_doms[snapshot_id] = dom
		logger.info(f"[Profiler] ShadowDOM parse: {time.time() - t1:.4f}s")

		# Build semantic deduplication mask to drop redundant visual clones
		try:
			t_mask = time.time()
			dedup_mask = ContentCoagulator._build_dedup_mask(dom.root)
			logger.info(f"[Profiler] Semantic dedup mask: {time.time() - t_mask:.4f}s (Masked {len(dedup_mask)} nodes)")
		except Exception as e:
			logger.warning(f"Failed to build dedup mask: {e}")
			dedup_mask = set()

		# Tag all content (for categories + DB persistence)
		logger.info("[Mapper] Running content tagger...")
		t2 = time.time()
		tagger = ContentTagger(dom, mask=dedup_mask)
		tagged = tagger.tag()
		self._active_tagged[snapshot_id] = tagged
		logger.info(f"[Profiler] ContentTagger: {time.time() - t2:.4f}s")

		content_count = len(tagged.all_content_xpaths())
		logger.info(f"[Mapper] Found {content_count} content xpaths, "
			f"{len(tagged.all_tags)} total tags")

		# Build content-only xpath tree (for DB persistence + label engine)
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
			# Persist content tree to DB
			t4 = time.time()
			self.store.save_content_tree(snapshot_id, url, content_tree)
			logger.info(f"[Profiler] DB persist tree: {time.time() - t4:.4f}s")

		return content_tree

	# ------------------------------------------------------------------
	# 4. LAYOUT — compute 3D coordinates from full tree
	# ------------------------------------------------------------------

	def layout(self, snapshot_id: str,
		offset_x: float = 0.0) -> List[Dict[str, Any]]:
		"""
		Compute 3D layout coordinates for the content-distilled tree
		using deterministic radial-tree placement (Fibonacci sphere + rings).
		
		Returns:
		    List of flat nodes with xpath, x, y, z, categories, depth.
		"""
		content_tree = self._active_trees.get(snapshot_id)
		if content_tree is None:
			content_tree = self.store.load_content_tree(snapshot_id)
			if content_tree is None:
				raise ValueError(f"No tree for snapshot {snapshot_id}")

		t0 = time.time()
		layout_struct = self._tree_to_layout_struct(content_tree)
		logger.info(f"[Profiler] tree_to_layout_struct: {time.time() - t0:.4f}s")

		# Prune contentless intermediate branch nodes
		t_prune = time.time()
		self._prune_contentless_branches(layout_struct)
		logger.info(f"[Profiler] prune_contentless_branches: {time.time() - t_prune:.4f}s")

		# Compute deterministic radial-tree layout coordinates.
		# LayoutGenerator assigns (layout_x, layout_y, layout_z) to every
		# node: Fibonacci sphere at root, radial rings at deeper levels.
		t_layout = time.time()
		LayoutGenerator.apply_radial_tree_layout(layout_struct)
		bounding_radius = LayoutGenerator.compute_bounding_radius(layout_struct)
		logger.info(f"[Profiler] radial_tree_layout: {time.time() - t_layout:.4f}s "
			f"(bounding_radius={bounding_radius:.1f})")

		# Flatten to list of nodes with server-computed coordinates
		t2 = time.time()
		flat = self._flatten_layout(layout_struct, offset_x, bounding_radius)
		self._active_layouts[snapshot_id] = flat
		logger.info(f"[Profiler] flatten_layout: {time.time() - t2:.4f}s")

		logger.info(f"[Mapper] Layout: {len(flat)} nodes")
		return flat

	# ------------------------------------------------------------------
	# 5. STREAM — push to GUI via callback
	# ------------------------------------------------------------------

	def stream(self, snapshot_id: str, url: str,
		callback: Callable, is_final: bool = True) -> None:
		"""
		Stream laid-out content nodes to the GUI via callback.
		
		Callback receives:
		    {'type': 'nodes', 'nodes': [...], 'links': [...],
		     'boundingRadius': float, 'offsetX': float,
		     'url': str, 'snapshot_id': str}
		
		Then:
		    {'type': 'done'}
		"""
		flat = self._active_layouts.get(snapshot_id)
		if flat is None:
			raise ValueError(f"No layout computed for {snapshot_id}")

		dom = self._active_doms.get(snapshot_id)
		if dom is None:
			html = self.store.load_snapshot_html(snapshot_id)
			if html:
				t0 = time.time()
				dom = ShadowDOM(html)
				logger.info(f"[Profiler] stream fallback ShadowDOM: {time.time() - t0:.4f}s")

		# O(N) optimization: build xpath to ShadowNode map
		t1 = time.time()
		xpath_to_node = {}
		if dom:
			for n in dom.iter_all():
				try:
					xp = get_absolute_xpath(n)
					if xp:
						xpath_to_node[xp] = n
				except Exception:
					pass
		logger.info(f"[Profiler] stream xpath_to_node map: {time.time() - t1:.4f}s")

		registry = TypeHandlerRegistry(base_url=url)
		ranker = InteractiveRanker()

		# Pass 1: Convert all to TypedDomNode
		t2 = time.time()
		typed_nodes = []
		for node in flat:
			xpath = node.get('xpath', '')

			# Fetch real text and attributes from DOM for Typed extraction
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
			typed_node._flat_ref = node # Attach for reference in Pass 2
			typed_nodes.append(typed_node)
		logger.info(f"[Profiler] stream TypedDomNode convert: {time.time() - t2:.4f}s")

		# Rank interactive elements across the snapshot
		t3 = time.time()
		ranker.rank_search_inputs(typed_nodes)
		ranker.rank_pagination_controls(typed_nodes)
		logger.info(f"[Profiler] stream interactive rank: {time.time() - t3:.4f}s")

		# Build analytics lookup from analyze() results
		analytics = self._active_analytics.get(snapshot_id, {})
		colored_nodes = analytics.get('colored_nodes', {})
		template_groups = analytics.get('template_groups', [])
		xpath_to_node_id = analytics.get('xpath_to_node_id', {})

		# Bulk-fetch labels for this URL so the stream carries them.  Folding
		# and knowledge-panel rendering both want to know which nodes are
		# labeled without issuing a DB query per node.
		labels_map: Dict[str, str] = {}
		try:
			for row in self.labels.get_labels_for_url(url):
				xp = row.get('xpath')
				lbl = row.get('label')
				if xp and lbl:
					labels_map[xp] = lbl
		except Exception as e:
			logger.debug(f"[Mapper] labels bulk-fetch skipped: {e}")

		# Build chunk lookup for structural-parent property injection.
		# We map each member xpath to a compact chunk descriptor and also
		# record which member xpath is the representative (is_chunk_root).
		chunk_lookup: Dict[str, Dict[str, Any]] = {}
		active_chunks = self._active_chunks.get(snapshot_id) or []
		if not active_chunks:
			# Fall back to DB-backed chunks for replay / load_snapshot paths.
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

		# Build template group lookup: node_id → (group_id, tier, pq_canonical)
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

		# Build nodes and links
		t4 = time.time()
		nodes = []
		links = []
		for typed_node in typed_nodes:
			node = typed_node._flat_ref
			node_xpath = typed_node.xpath
			node_id = f"{url}:{node_xpath}"

			# Derive a display name using typed fields
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

			# Inject chunk membership as node properties. The chunk's
			# representative xpath is tagged is_chunk_root=true so the GUI
			# can render the knowledge panel from that node.
			ch_info = chunk_lookup.get(node_xpath)
			if ch_info:
				node_dict.update(ch_info)

			# Inject analytics fields from analyze() results
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
		logger.info(f"[Profiler] stream build final lists: {time.time() - t4:.4f}s")

		# Orphan fix: any structure edge pointing at a non-emitted parent
		# gets its target walked up to the nearest emitted ancestor so the
		# node is not stranded as a disconnected sphere in the 3D layout.
		# Without this step the distiller's contentless-branch pruning can
		# produce edges whose target xpath was never emitted.
		t4b = time.time()
		emitted_ids = {n['id'] for n in nodes}
		root_id = f"{url}:/" # synthetic root always emitted with xpath='/'
		for link in links:
			if link.get('type') != 'structure':
				continue
			if link['target'] in emitted_ids:
				continue
			parent_xp = link.get('parent_xpath', '')
			# Walk up the xpath chain looking for an emitted ancestor.
			cur = parent_xp
			resolved = None
			while cur and cur != '/':
				cur = cur.rstrip('/').rsplit('/', 1)[0] or '/'
				candidate = f"{url}:{cur}"
				if candidate in emitted_ids:
					resolved = candidate
					break
			link['target'] = resolved or root_id
		logger.info(f"[Profiler] stream orphan repair: {time.time() - t4b:.4f}s")

		# Append cross-page edges from loop closure
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
				logger.debug(f"[Mapper] Cross-page edge generation skipped: {e}")

		bounding_radius = flat[0].get('bounding_radius', 50) if flat else 50
		offset_x = flat[0].get('offset_x', 0) if flat else 0

		# Always full-send — no delta comparison
		t5 = time.time()
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
		logger.info(f"[Profiler] stream WS push: {time.time() - t5:.4f}s")

		if is_final:
			callback({'type': 'done'})

	# ------------------------------------------------------------------
	# 6. RELEASE — free memory
	# ------------------------------------------------------------------

	def release(self, snapshot_id: str) -> None:
		"""Release in-memory DOM and tree objects for a snapshot."""
		self._active_doms.pop(snapshot_id, None)
		self._active_trees.pop(snapshot_id, None)
		self._active_tagged.pop(snapshot_id, None)
		self._active_layouts.pop(snapshot_id, None)
		self._active_analytics.pop(snapshot_id, None)
		self._active_chunks.pop(snapshot_id, None)
		logger.info(f"[Mapper] Released memory for snapshot {snapshot_id}")

	# ------------------------------------------------------------------
	# 6b. CHUNK — partition distilled DOM into SLM-sized chunks
	# ------------------------------------------------------------------

	def _build_chunks_for_streaming(
		self, snapshot_id: str, url: str,
		char_budget: int = DEFAULT_CHAR_BUDGET,
	) -> Tuple[List[Chunk], List[Any]]:
		"""Build chunks + render instances WITHOUT embedding or DB persistence.

		Used by the per-iteration absorber path so each scroll yield can
		stream a fresh chunk view to the frontend in tens of milliseconds
		instead of paying the embedding model's per-instance cost on every
		iteration. The absorber dedups across iterations; embedding +
		``ChunkInstance`` persistence happen ONCE at the end of the scan
		over the absorber's final settled state.

		Returns ``(chunks, instances)`` — instances have ``embedding=None``
		and have NOT been written to the database yet.
		"""
		tree = self._active_trees.get(snapshot_id)
		if tree is None:
			return [], []

		dom = self._active_doms.get(snapshot_id)
		if dom is None and url in self._last_dom_for_url:
			dom = self._last_dom_for_url[url]

		t0 = time.time()
		xpath_map = build_xpath_node_map(dom)
		text_provider = build_text_provider_from_dom(dom, xpath_map=xpath_map)
		structure_provider = build_structure_provider_from_dom(dom, xpath_map=xpath_map)

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
				logger.exception(
					"[Mapper] streaming render_all_chunks failed; "
					"emitting chunks without instances",
				)

		logger.info(
			"[Profiler] streaming chunk-build: %.4fs (%d chunks, %d instances)",
			time.time() - t0, len(chunks), len(instances),
		)
		return chunks, instances

	def chunk(self, snapshot_id: str, url: str,
		char_budget: int = DEFAULT_CHAR_BUDGET,
		persist: bool = True) -> Tuple[List[Chunk], List[Any]]:
		"""
		Run the post-scan chunking pass on the distilled DOM for a snapshot.
		
		Walks each content-bearing leaf upward until a subtree exceeds the
		text-character budget (hyperlinks and media excluded from the
		count). Uses the previous step as the chunk boundary. Chunks that
		share a generalized xpath pattern are emitted as a single group
		with N members; all leaves inside those member subtrees are
		claimed so we never partition the same content twice.
		"""
		tree = self._active_trees.get(snapshot_id)
		if tree is None:
			tree = self.store.load_content_tree(snapshot_id)
		if tree is None:
			logger.warning(f"[Mapper] chunk() — no content tree for {snapshot_id}")
			return []

		dom = self._active_doms.get(snapshot_id)
		if dom is None and url in self._last_dom_for_url:
			dom = self._last_dom_for_url[url]

		t0 = time.time()
		# One O(N) DOM walk shared by text provider, structure provider,
		# and render_all_chunks — avoids the legacy triple traversal.
		xpath_map = build_xpath_node_map(dom)
		text_provider = build_text_provider_from_dom(dom, xpath_map=xpath_map)
		structure_provider = build_structure_provider_from_dom(dom, xpath_map=xpath_map)

		tagged = self._active_tagged.get(snapshot_id)
		all_tags = tagged.all_tags if tagged else []
		logger.info(f"[Mapper] Generating chunks with {len(all_tags)} active tags")

		builder = ChunkBuilder(
			tree, text_provider,
			char_budget=char_budget, all_tags=all_tags,
			structure_provider=structure_provider,
		)
		chunks = builder.build(snapshot_id=snapshot_id)
		logger.info(f"[Profiler] ChunkBuilder: {time.time() - t0:.4f}s "
			f"({len(chunks)} chunks, budget={char_budget})")

		self._active_chunks[snapshot_id] = chunks
		instances = []
		if persist and chunks:
			t1 = time.time()
			self.store.save_chunks(snapshot_id, url, chunks)
			logger.info(f"[Profiler] DB persist chunks: {time.time() - t1:.4f}s")

			# Render + embed + persist ChunkInstance rows so the 3D
			# projector and retrieval endpoints have data to work with.
			# Without this the UI polls /api/chunk_nodes forever (the
			# legacy path only wrote ContentChunk rows, not ChunkInstance).
			try:
				instances = self._embed_and_persist_instances(
					snapshot_id=snapshot_id, url=url, chunks=chunks, dom=dom,
					xpath_map=xpath_map,
				)
			except Exception:
				logger.exception(
					"[Mapper] embed+persist ChunkInstance rows failed",
				)

		return chunks, instances

	def _embed_and_persist_instances(
		self, *, snapshot_id: str, url: str,
		chunks: List[Chunk], dom,
		xpath_map=None,
		instances: Optional[List[Any]] = None,
	) -> List[Any]:
		"""Render every chunk, embed it, and upsert ``ChunkInstance`` rows.

		Returns the embedded instances. Silently returns [] when
		the DOM isn't available or the renderer produces nothing — the
		caller has already logged the chunk count so we don't re-log
		here unless we actually did work.

		Pass ``instances`` if the caller has already rendered them (e.g.
		the per-iteration absorber path) — the renderer is skipped and
		the supplied instances are embedded + persisted in place.
		"""
		if not chunks:
			return []
		if instances is None and dom is None:
			return []

		from backend.services.chunk_instance_embedder import ChunkInstanceEmbedder
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

		# Lazy-cache a single embedder on the mapper so we don't reload
		# the GPU model on every scan. Multiple back-to-back scans share
		# the same weights.
		embedder = getattr(self, "_chunk_embedder", None)
		if embedder is None:
			embedder = ChunkInstanceEmbedder()
			self._chunk_embedder = embedder

		t1 = time.time()
		batch = embedder.embed_instances(instances)
		logger.info(
			"[Profiler] embed_instances: %.3fs (%d unique texts, %d instances)",
			time.time() - t1, batch.unique_text_count, batch.embedded_count,
		)

		conn = get_connection()
		# ``version_id`` is a free-form STRING in the schema; reusing the
		# snapshot_id gives us a stable per-scan namespace without
		# needing to first persist a TrieVersion row.
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
				logger.exception(
					"[Mapper] PageEmbedding persist failed (instances still saved)",
				)

		logger.info(
			"[Profiler] ChunkInstance persist total: %.3fs (%d row(s))",
			time.time() - t0, n,
		)
		return instances

	def get_chunks(self, snapshot_id: str) -> List[Dict[str, Any]]:
		"""Return chunks as plain dicts — active cache first, else DB."""
		active = self._active_chunks.get(snapshot_id)
		if active is not None:
			return [c.as_dict() for c in active]
		return self.store.load_chunks(snapshot_id)

	def apply_chunk_label(self, chunk_id: str, label: str,
		snapshot_id: str = None) -> bool:
		"""Manually set a chunk's label (e.g. 'card', 'nav'). Persists."""
		ok = self.store.set_chunk_label(chunk_id, label)
		if ok and snapshot_id and snapshot_id in self._active_chunks:
			for ch in self._active_chunks[snapshot_id]:
				if ch.chunk_id == chunk_id:
					ch.label = label or None
					break
		return ok

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
	# Full pipeline
	# ------------------------------------------------------------------

	def snapshot(self, url: str, max_duration: int = 60,
		pause: float = 1.0, offset_x: float = 0.0,
		on_stream: Callable = None) -> Dict[str, Any]:
		"""
		Run the full pipeline: scan → distill → layout → stream (full-send) → release.
		"""
		t_start = time.time()

		if not self.driver:
			raise RuntimeError("No WebDriver attached to mapper")

		current_snapshot_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

		# (Delta tracking removed — always full-send)

		content_tree = {}
		flat_layout = []
		content_xpaths = []
		dom = None

		# Minimum new-node count that warrants a full distill + GUI stream.
		# Iterations that add fewer nodes (navigation chrome, ads, etc.) still
		# update the master tree via the scanner's merge pass but skip the
		# expensive ShadowDOM parse → tagger → layout → WebSocket push cycle.
		# The final state is always emitted regardless of this threshold.
		_STREAM_MIN_NEW_NODES = 3
		_scan_iter = 0
		_last_distilled_iter = 0

		# Continuous-streaming chunk dedup. One absorber per snapshot
		# accumulates chunks across scroll iterations; the same pattern
		# emitted twice (12 cards → 24 cards) results in a chunk_replaced
		# event so the frontend drops the superseded chunk before drawing
		# the new one. Lives DOWNSTREAM of the scanner/distiller because
		# absorption is a semantic (chunk-pattern, member-set) operation.
		absorber = ChunkAbsorber()

		# Per-iteration chunk-build is EXPENSIVE (ChunkBuilder.build +
		# render_all_chunks together cost ~80–250 ms per call on a
		# typical 800-node distilled trie). Running it on every distill
		# iteration multiplies total scan time by N. Instead we DEBOUNCE
		# absorber emission: only run the streaming chunk-build when
		#   (a) at least ``_ABSORB_NEW_NODE_DELTA`` new nodes have
		#       accumulated since the last absorber emission AND
		#   (b) at least ``_ABSORB_MIN_INTERVAL_S`` seconds have passed
		#       since the last absorber emission, AND content_tree is
		#       non-empty.
		# Final flush always emits regardless so the absorber sees the
		# settled state. With the defaults we get ~3-6 emissions per
		# scan (vs 12-30 distill iterations), keeping per-scan absorber
		# overhead well under one second on average pages.
		_ABSORB_NEW_NODE_DELTA = 60
		_ABSORB_MIN_INTERVAL_S = 1.5
		_absorb_state = {"nodes": 0, "last_t": 0.0}

		def _process_distill(master_tree_to_process, added_nodes_to_process, is_final_flush=False):
			nonlocal content_tree, flat_layout, content_xpaths, dom

			t_iter = time.time()
			html = serialize_to_html(master_tree_to_process)

			dom = ShadowDOM(html)
			self._active_doms[current_snapshot_id] = dom

			try:
				dedup_mask = ContentCoagulator._build_dedup_mask(dom.root)
			except Exception as e:
				logger.warning(f"[Mapper] Dedup mask failed: {e}")
				dedup_mask = set()

			tagger = ContentTagger(dom, mask=dedup_mask)
			tagged = tagger.tag()
			self._active_tagged[current_snapshot_id] = tagged

			content_xpaths = tagged.all_content_xpaths()
			total_dom_nodes = sum(1 for _ in dom.iter_all())

			log_prefix = "final-flush" if is_final_flush else f"iter={_scan_iter}"
			logger.info(f"[Mapper] {log_prefix} +{len(added_nodes_to_process)} nodes | "
				f"content {len(content_xpaths)}/{total_dom_nodes} "
				f"({len(dedup_mask)} masked) | "
				f"elapsed {time.time()-t_iter:.2f}s")

			builder = XPathTreeBuilder()
			builder.add_tagged_content(tagged)
			content_tree = builder.build()
			self._active_trees[current_snapshot_id] = content_tree

			trie_nodes = count_content_nodes(content_tree)
			logger.info(f"[Mapper] Patricia trie: {trie_nodes} content leaves")

			flat_layout = self.layout(current_snapshot_id, offset_x=offset_x)

			if on_stream:
				self.stream(current_snapshot_id, url, on_stream, is_final=False)

			# Build chunks for THIS iteration (no embed, no DB persist —
			# those run once at the end over the absorber's final state)
			# and route them through the absorber so the frontend gets a
			# stream of chunk_added / chunk_replaced events instead of
			# waiting until the entire scan finishes.
			#
			# DEBOUNCE: only invoke the streaming chunk-build when enough
			# new nodes have accumulated AND enough wall-clock has passed
			# since the last absorber emission. Without this gate every
			# distill iteration would pay the chunk-build cost (~100ms),
			# multiplying total scan time by the iteration count and
			# defeating the point of streaming. Final flush always emits
			# so the absorber holds the settled state at scan-end.
			_absorb_state["nodes"] += len(added_nodes_to_process)
			now = time.time()
			should_emit = (
				is_final_flush
				or (
					_absorb_state["nodes"] >= _ABSORB_NEW_NODE_DELTA
					and (now - _absorb_state["last_t"]) >= _ABSORB_MIN_INTERVAL_S
				)
			)
			# Always emit on the very first qualified iteration so the
			# user sees SOMETHING right away — last_t == 0 starts the
			# scan, so the time-since check above passes naturally.

			if should_emit and content_tree:
				try:
					iter_chunks, iter_instances = self._build_chunks_for_streaming(
						current_snapshot_id, url,
					)
				except Exception:
					logger.exception(
						"[Mapper] iteration chunk-build failed (continuing)"
					)
					iter_chunks, iter_instances = [], []

				_absorb_state["nodes"] = 0
				_absorb_state["last_t"] = now

				if iter_chunks:
					events = absorber.absorb(iter_chunks, iter_instances)
					if on_stream:
						for ev in events:
							# Suppress chunk_unchanged from the wire by
							# default — the frontend already has the
							# chunk; emitting again is just noise. The
							# absorber still tracks it internally so a
							# later iteration that grows the member set
							# correctly emits chunk_replaced.
							if ev.kind == "chunk_unchanged":
								continue
							try:
								on_stream(ChunkAbsorber.event_to_payload(
									ev, snapshot_id=current_snapshot_id, url=url,
								))
							except Exception:
								logger.exception(
									"[Mapper] on_stream(absorber event) failed",
								)

		last_master_tree = None

		for master_tree, added_nodes in self.scan(url, max_duration=max_duration, pause=pause):
			_scan_iter += 1
			last_master_tree = master_tree

			# Skip the expensive distill for trivial increments so the scanner
			# can keep scrolling without blocking on a full DOM rebuild.
			if _scan_iter > 1 and len(added_nodes) < _STREAM_MIN_NEW_NODES:
				logger.debug(
					"[Mapper] Skipping intermediate distill: only %d new node(s)", len(added_nodes)
				)
				continue

			_process_distill(master_tree, added_nodes)
			_last_distilled_iter = _scan_iter

		if last_master_tree is not None and _last_distilled_iter != _scan_iter:
			logger.debug("[Mapper] Processing final skipped distill iteration")
			_process_distill(last_master_tree, [], is_final_flush=True)

		# Guarantee the absorber's settled state matches the final
		# distilled DOM. The gating thresholds may have skipped the
		# LAST iteration's emission (e.g. last iter added 30 new
		# nodes — under the 60-node delta), so without a final pass
		# the post-loop embed+persist could write stale chunk
		# membership. Skip the final chunk-build entirely if no new
		# nodes have accumulated since the most recent emission —
		# in that case the absorber already holds the final tree.
		if content_tree and _absorb_state["nodes"] > 0:
			try:
				final_chunks, final_instances = self._build_chunks_for_streaming(
					current_snapshot_id, url,
				)
			except Exception:
				logger.exception(
					"[Mapper] final absorber chunk-build failed (continuing)"
				)
				final_chunks, final_instances = [], []

			if final_chunks:
				final_events = absorber.absorb(final_chunks, final_instances)
				if on_stream:
					for ev in final_events:
						if ev.kind == "chunk_unchanged":
							continue
						try:
							on_stream(ChunkAbsorber.event_to_payload(
								ev, snapshot_id=current_snapshot_id, url=url,
							))
						except Exception:
							logger.exception(
								"[Mapper] on_stream(final absorber event) failed",
							)

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

		# Save distilled source HTML and Patricia trie to DB
		_prune_dom_to_content(dom.root, set(content_xpaths))
		distilled_html = serialize_shadow_node(dom.root)
		self.store.save_snapshot(url, distilled_html, snapshot_id=current_snapshot_id)
		self.store.save_content_tree(current_snapshot_id, url, content_tree)

		# Persist the last DOM and content tree per URL so search/detail
		# queries work after release() clears the per-snapshot caches.
		if current_snapshot_id in self._active_doms:
			self._last_dom_for_url[url] = self._active_doms[current_snapshot_id]
		if content_tree:
			self._last_tree_for_url[url] = content_tree
		self._last_snapshot_for_url[url] = current_snapshot_id

		# Post-scan finalization: take the absorber's settled chunks +
		# already-rendered instances, embed them ONCE, and persist to
		# the DB. The chunk_added / chunk_replaced events have already
		# streamed live above so the frontend has been drawing for the
		# whole scan; this final pass just upgrades the wire payload
		# with embedding vectors and writes everything to disk.
		chunks: List[Chunk] = absorber.current_chunks() if content_tree else []
		instances: List[Any] = absorber.current_instances() if content_tree else []

		if chunks:
			try:
				self._active_chunks[current_snapshot_id] = chunks
				self.store.save_chunks(current_snapshot_id, url, chunks)
			except Exception:
				logger.exception("[Mapper] save_chunks failed")

			if instances:
				try:
					instances = self._embed_and_persist_instances(
						snapshot_id=current_snapshot_id, url=url,
						chunks=chunks, dom=self._active_doms.get(current_snapshot_id),
						instances=instances,
					)
				except Exception:
					logger.exception(
						"[Mapper] embed+persist on absorber state failed",
					)

		# Final consolidated emission. The frontend has been receiving
		# chunk_added / chunk_replaced incrementally; this final batch
		# carries the freshly-embedded vectors so anything cached on
		# the client picks up retrieval-ready embeddings.
		if on_stream and chunks:
			on_stream({
				'type': 'chunks',
				'snapshot_id': current_snapshot_id,
				'url': url,
				'chunks': [c.as_dict() for c in chunks],
			})

		if on_stream and instances:
			on_stream({
				'type': 'chunk_instances',
				'snapshot_id': current_snapshot_id,
				'url': url,
				'instances': [
					{
						"chunk_id": inst.chunk_id,
						"instance_id": inst.instance_id(url),
						"instance_idx": inst.instance_idx,
						"pattern": inst.pattern,
						"absolute_xpath": inst.absolute_xpath,
						"html_raw": inst.html_raw,
						"rendered_text": inst.rendered_text,
						"fields": inst.fields,
						"embedding": inst.embedding if inst.embedding is not None else None,
						"image_url": inst.image_url,
						"link_url": inst.link_url
					}
					for inst in instances
				]
			})

		if on_stream:
			on_stream({'type': 'done', 'snapshot_id': current_snapshot_id})

		self.release(current_snapshot_id)

		logger.info(f"[Mapper] Pipeline complete: produced {len(chunks)} chunks and {len(instances)} instances.")
		logger.info(f"[Profiler] TOTAL SNAPSHOT PIPELINE: {time.time() - t_start:.4f}s")
		return {
			'snapshot_id': current_snapshot_id,
			'is_new': True,
			'node_count': count_content_nodes(content_tree) if content_tree else 0,
			'bounding_radius': flat_layout[0].get('bounding_radius', 50) if flat_layout else 50,
			'url': url,
			'chunk_count': len(chunks),
			'dom': self._last_dom_for_url.get(url)
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
