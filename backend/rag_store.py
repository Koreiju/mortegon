"""
rag_store_v2.py — Fibre Web Haptics
Extended Graph Database Ontology & Retrieval Store.

Extends rag_store.py with:
	- Prompt node: tracks user search prompts across multiple URLs
	- SearchField / PaginationButton nodes: caches detected interface elements per URL
	- Alt-text aware embedding: extracts alt= attributes for media elements
	- Whitespace-cleaned vectorization: normalizes text before embedding
	- URL path decomposition: breaks URLs into component segments in the graph
	- Prompt-to-URL tracking edges for multi-page search sessions

Ontology v4 Schema:
	Nodes:
		- Page (url, domain, timestamp)
		- Chunk (chunk_id_str, stem_selector, subtree_root, frequency, category flags)
		- Sample (sample_id, content, is_text, has_alt, embedding)
		- UrlPattern (pattern)
		- UrlPath (segment, full_path)
		- Prompt (prompt_id, prompt_text, timestamp)
		- DetectedField (field_id, field_type, selector, url)

	Edges:
		- Page -CONTAINS-> Chunk
		- Chunk -HAS_SAMPLE-> Sample
		- Page -HAS_PATTERN-> UrlPattern
		- Page -HAS_PATH_ROOT-> UrlPath
		- UrlPath -NEXT_SEGMENT-> UrlPath
		- Page -LINKED_TO_PROMPT-> Prompt
		- Page -HAS_DETECTED_FIELD-> DetectedField
		- Chunk -WAS_USED_FOR-> Action
		- Page -HAS_ACTION-> Action
"""

import os
import re
import time
import json 
import logging
import hashlib
import numpy as np
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
from urllib.parse import urlparse, urljoin


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

NOMIC_EMBED_DIM = 768
DEFAULT_RAG_TOP_K = 5
MAX_EMBED_TEXT_LEN = 512
MAX_SAMPLES_HIGH_FREQ = 10
HIGH_FREQ_THRESHOLD = 15


# ======================================================================
# TEXT CLEANING UTILITIES
# ======================================================================
def clean_text_for_embedding(text: str) -> str:
	"""Normalize whitespace and strip artifacts for clean embedding input."""
	if not text or not isinstance(text, str):
		return ""

	# Remove HTML entities
	text = re.sub(r'&[a-z]+;', ' ', text)

	# Collapse all whitespace sequences
	text = re.sub(r'\s+', ' ', text)

	# Remove control characters and zero-width spaces
	text = re.sub(r'[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202f]', '', text)

	# Remove URLs (they're separate anyway)
	text = re.sub(r'https?://\S+', '', text)

	# Remove common web artifacts
	text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
	text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

	# Trim and return
	return text.strip()


def extract_embeddable_text(sample: dict) -> str:
	"""
	Extract all text fields from a chunk sample for embedding.
	Enhanced to handle more text sources and better cleaning.
	"""
	parts = []

	# Collect text from all possible fields
	text_fields = [
		sample.get('text', ''),
		sample.get('content', ''),
		sample.get('alt', ''),
		sample.get('title', ''),
		sample.get('aria-label', '') or sample.get('aria_label', ''),
		sample.get('placeholder', ''),
		sample.get('value', ''),
		sample.get('name', '')
	]

	# Add input attributes
	input_attrs = sample.get('input_attrs', {})
	if input_attrs:
		for key in ['placeholder', 'value', 'title', 'aria-label', 'name']:
			if key in input_attrs:
				text_fields.append(input_attrs[key])

	# Add button text
	btn_info = sample.get('button_info', {})
	if btn_info and 'text' in btn_info:
		text_fields.append(btn_info['text'])

	# Clean and combine all text
	for text in text_fields:
		if text and isinstance(text, str):
			cleaned = clean_text_for_embedding(text)
			if cleaned and len(cleaned) > 2: # Skip very short strings
				parts.append(cleaned)

	# Remove duplicates while preserving order
	seen = set()
	unique_parts = []
	for part in parts:
		if part not in seen:
			seen.add(part)
			unique_parts.append(part)

	return ' '.join(unique_parts)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
	"""Compute cosine similarity between two vectors."""
	norm_a = np.linalg.norm(a)
	norm_b = np.linalg.norm(b)

	if norm_a == 0 or norm_b == 0:
		return 0.0

	return float(np.dot(a, b) / (norm_a * norm_b))


def compute_content_hash(text: str) -> str:
	"""Compute a short hash for deduplication."""
	return hashlib.md5(text.encode('utf-8', errors='replace')).hexdigest()[:12]


def normalize_chunk_samples(chunk: dict) -> list:
	"""
	Normalize chunk samples to a flat list of node-level sample dicts.
	Handles both:
	  - Flat format: [{'tag': 'p', 'text': '...', 'links': [...]}]
	  - Nested selector_samples: [{'selector': '...', 'samples': [{'tag': 'p', ...}]}]
	"""
	raw = chunk.get('samples', [])
	flat = []
	for s in raw:
		if not isinstance(s, dict):
			continue
		# Nested format: selector_sample with 'samples' key
		if 'samples' in s and isinstance(s['samples'], list):
			for inner in s['samples']:
				if isinstance(inner, dict):
					flat.append(inner)
		# Flat format: already a node-level sample dict
		elif 'tag' in s or 'text' in s or 'links' in s or 'alt' in s:
			flat.append(s)
		# Selector_samples with no matching samples: skip
	return flat


def decompose_url(url: str) -> List[Dict[str, str]]:
	"""Decompose a URL into its path segment nodes for graph storage."""
	parsed = urlparse(url)
	segments = [s for s in parsed.path.split('/') if s]
	nodes = []
	accumulated = parsed.netloc
	for seg in segments:
		accumulated = f"{accumulated}/{seg}"
		nodes.append({
			'segment': seg,
			'full_path': accumulated,
		})
	return nodes


# ======================================================================
# EMBEDDER
# ======================================================================
class NomicEmbedder:
	"""Wraps Nomic local embedding (nomic-embed-text-v1.5)."""

	def __init__(self, device: str = "cuda", model: str = "nomic-embed-text-v1.5"):
		self.device = device
		self.model = model
		self._embed_fn = None
		self._available = False
		self._initialize_embedder()

	def _initialize_embedder(self):
		"""Initialize the Nomic embedder."""
		try:
			from nomic import embed
			self._embed_fn = embed.text
			self._available = True
			logger.info(f"Nomic embed available (model={self.model}, device={self.device})")
		except ImportError as e:
			logger.error(f"Nomic not installed: {e}")
			raise ImportError("Nomic embed-text package not installed. Please install with: pip install nomic")

	def embed_texts(self, texts: List[str], task_type: str = "search_document") -> np.ndarray:
		"""Embed texts with proper error handling."""
		if not texts:
			return np.zeros((0, NOMIC_EMBED_DIM), dtype=np.float32)

		# Clean & truncate
		texts = [clean_text_for_embedding(t)[:MAX_EMBED_TEXT_LEN] for t in texts]

		if not self._available:
			raise RuntimeError("Nomic embedder not available. Please check installation.")

		try:
			output = self._embed_fn(
				texts=texts, 
				model=self.model, 
				task_type=task_type,
				inference_mode="local", 
				device=self.device,
			)
			return np.array(output['embeddings'], dtype=np.float32)
		except Exception as e:
			logger.error(f"Nomic embedding failed: {e}")
			raise RuntimeError(f"Embedding failed: {e}")

	def embed_query(self, query: str) -> np.ndarray:
		"""Embed a single query."""
		return self.embed_texts([query], task_type="search_query")[0]

# ======================================================================
# FIBRE GRAPH STORE V2
# ======================================================================

class FibreGraphStoreV2:
	"""
	Extended Kuzu-backed Graph Database.
	
	New over v1:
	  - Prompt tracking across URLs
	  - DetectedField caching (search/pagination)
	  - Alt-text aware embedding
	  - Whitespace-cleaned vectorization
	  - Deduplication via content hashing
	"""

	def __init__(self, db_path: str = "fibre_graph_v2.kuzu", embed_device: str = "cuda", shared_db=None, disable_embed=False):
		self.db_path = Path(db_path)
		self.embedder = NomicEmbedder(device=embed_device) if not disable_embed else None
		self._db = shared_db
		self._injected_conn = None
		self._initialized = False
		# In-memory dedup cache: content_hash -> sample_id
		self._sample_hash_cache: Dict[str, str] = {}
		self._batch_nodes: List[Dict] = []
		self._batch_edges: List[Dict] = []

	def _get_conn(self):
		import kuzu
		import shutil
		if self._db is None:
			if self.db_path.exists() and self.db_path.is_dir():
				try:
					# check if directory is empty
					if not any(self.db_path.iterdir()):
						shutil.rmtree(self.db_path)
				except Exception as e:
					logger.warning(f"Could not clean up empty database directory: {e}")

			self._db = kuzu.Database(str(self.db_path))
		return kuzu.Connection(self._db)

	def initialize(self):
		"""Define the full v2 schema ontology."""
		print("[RAG-DB Debug] >>> Validating native schema ontology structure...")
		if self._initialized:
			print("[RAG-DB Debug] >>> Fast-skipping schema verification (already cached).")
			return
		print("[RAG-DB Debug] >>> Creating robust underlying KuzuDB graph pointers...")
		conn = self._get_conn()

		# --- NODE TABLES ---
		tables = [
			("Page", "url STRING, domain STRING, timestamp STRING, PRIMARY KEY (url)"),
			("Chunk", """chunk_id_str STRING, stem_selector STRING, subtree_root STRING,
				frequency INT64, is_input BOOL, is_button BOOL, is_text BOOL,
				is_link BOOL, has_url_pattern BOOL, has_structure BOOL, PRIMARY KEY (chunk_id_str)"""),
			("Sample", f"""sample_id STRING, content STRING, is_text BOOL,
				has_alt BOOL, content_hash STRING,
				embedding FLOAT[{NOMIC_EMBED_DIM}], PRIMARY KEY (sample_id)"""),
			("UrlPattern", "pattern STRING, PRIMARY KEY (pattern)"),
			("UrlPath", "segment STRING, full_path STRING, PRIMARY KEY (full_path)"),
			("Prompt", "prompt_id STRING, prompt_text STRING, timestamp STRING, PRIMARY KEY (prompt_id)"),
			("DetectedField", """field_id STRING, field_type STRING, selector STRING,
				url STRING, PRIMARY KEY (field_id)"""),
			("Action", """action_id STRING, action_type STRING, success BOOL,
				timestamp STRING, PRIMARY KEY (action_id)"""),
			# Scraping table (node)
			("DomNode", """node_id STRING, node_type INT64, tag_name STRING, node_name STRING,
				id_attr STRING, class_name STRING, attributes STRING, text_content STRING,
				signature STRING, page_url STRING, content_hash STRING, PRIMARY KEY (node_id)"""),
		]

		for name, schema in tables:
			try:
				conn.execute(f"CREATE NODE TABLE {name}({schema})")
			except Exception:
				pass

		try:
			conn.execute("CREATE INDEX IF NOT EXISTS idx_domnode_url ON DomNode (page_url);")
		except Exception:
			pass

		# --- RELATIONSHIP TABLES ---
		rels = [
			("CONTAINS", "Page", "Chunk"),
			("HAS_SAMPLE", "Chunk", "Sample"),
			("HAS_PATTERN", "Page", "UrlPattern"),
			("HAS_PATH_ROOT", "Page", "UrlPath"),
			("NEXT_SEGMENT", "UrlPath", "UrlPath"),
			("LINKED_TO_PROMPT", "Page", "Prompt"),
			("HAS_DETECTED_FIELD", "Page", "DetectedField"),
			("WAS_USED_FOR", "Chunk", "Action"),
			("HAS_ACTION", "Page", "Action"),
			# New relationships for DOM tree
			("PARENT_OF", "DomNode", "DomNode"),
			("HAS_SHADOW_ROOT", "DomNode", "DomNode"),
		]
		for name, src, dst in rels:
			try:
				conn.execute(f"CREATE REL TABLE {name}(FROM {src} TO {dst})")
			except Exception:
				pass

		self._initialized = True
		logger.info("FibreGraphStoreV2: Schema initialized.")

	# ------------------------------------------------------------------
	# Web Scraping 
	# ------------------------------------------------------------------
	def get_node_signatures(self, url: str) -> Set[str]:
		"""Return all node signatures stored for a given URL."""
		self.initialize()
		conn = self._get_conn()
		res = conn.execute("MATCH (n:DomNode {page_url: $url}) RETURN n.signature", {'url': url})
		return {r[0] for r in self._iter_results(res)}

	def get_content_hashes_for_url(self, url: str) -> Set[str]:
		"""Retrieve all text content hashes previously captured for a URL to prune snapshots."""
		self.initialize()
		conn = self._get_conn()
		try:
			res = conn.execute(
				"MATCH (n:DomNode {page_url: $url}) WHERE n.content_hash IS NOT NULL AND n.content_hash <> '' RETURN n.content_hash",
				{'url': url}
			)
			return {r[0] for r in self._iter_results(res)}
		except Exception as e:
			logger.error(f"Failed to get content hashes: {e}")
			return set()

	def index_dom_snapshot(self, snapshot_json: dict, page_url: str) -> str:
		"""Insert a full DOM snapshot, merging with existing nodes.
		Returns the root node id."""
		# Reset batch collections
		self._batch_nodes.clear()
		self._batch_edges.clear()
		root_id = self._insert_dom_node(snapshot_json, page_url)
		self._flush_dom_batch()
		return root_id

	def get_dom_root(self, page_url: str) -> Optional[str]:
		"""Retrieve the root DomNode id for a given page."""
		conn = self._get_conn()
		res = conn.execute("""
			MATCH (n:DomNode {page_url: $url})
			WHERE NOT (n)<-[:PARENT_OF]-()
			RETURN n.node_id LIMIT 1
		""", {'url': page_url})
		rows = self._iter_results(res)
		return rows[0][0] if rows else None

	def serialize_dom_to_html(self, page_url: str) -> str:
		"""Reconstruct the full HTML for a page from the graph."""
		root_id = self.get_dom_root(page_url)
		if not root_id:
			return ""
		nodes, children = self._get_dom_tree(page_url)
		return self._build_html(root_id, nodes, children)

	def _get_dom_tree(self, page_url: str):
		"""Fetch all DomNodes and edges for a page.
		   Returns (nodes_dict, children_dict)."""
		conn = self._get_conn()
		
		# 1. Get minimal node parameters optimized
		nodes_res = conn.execute("""
			MATCH (n:DomNode {page_url: $url})
			RETURN n.node_id, n.node_type, n.tag_name, n.node_name, n.attributes, n.text_content
		""", {'url': page_url})
		
		nodes = {}
		for row in self._iter_results(nodes_res):
			node_id, node_type, tag_name, node_name, attributes, text_content = row
			nodes[node_id] = {
				'node_id': node_id,
				'node_type': node_type,
				'tag_name': tag_name,
				'node_name': node_name,
				'attributes': attributes,
				'text_content': text_content
			}

		# 2. Get light DOM parent-child relationships
		light_res = conn.execute("""
			MATCH (parent:DomNode)-[:PARENT_OF]->(child:DomNode)
			WHERE parent.page_url = $url
			RETURN parent.node_id, child.node_id
		""", {'url': page_url})

		# 3. Get shadow DOM parent-child relationships
		shadow_res = conn.execute("""
			MATCH (parent:DomNode)-[:HAS_SHADOW_ROOT]->(child:DomNode)
			WHERE parent.page_url = $url
			RETURN parent.node_id, child.node_id
		""", {'url': page_url})
		
		children = {}  # parent_id -> {'light': [], 'shadow': []}
		for row in self._iter_results(light_res):
			parent_id, child_id = row
			if parent_id not in children:
				children[parent_id] = {'light': [], 'shadow': []}
			children[parent_id]['light'].append(child_id)

		for row in self._iter_results(shadow_res):
			parent_id, child_id = row
			if parent_id not in children:
				children[parent_id] = {'light': [], 'shadow': []}
			children[parent_id]['shadow'].append(child_id)

		return nodes, children

	def _build_html(self, root_id: str, nodes: dict, children: dict) -> str:
		"""Iteratively build HTML from pre-fetched nodes and children using optimal templating."""
		result_parts = []
		stack = [(root_id, 'enter')]

		void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img',
						 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

		while stack:
			item = stack.pop()
			if len(item) == 1:
				# Support direct string injections for the template wrappers
				result_parts.append(item[0])
				continue
				
			node_id, state = item
			props = nodes.get(node_id)
			if not props:
				continue

			if state == 'exit':
				# Add closing tag for elements
				if props.get('node_type') == 1:
					tag = props.get('tag_name')
					if tag not in void_elements:
						result_parts.append(f"</{tag}>")
				continue

			# state == 'enter'
			ntype = props.get('node_type')

			# Handle non-element nodes
			if ntype == 3:  # text
				text = props.get('text_content', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
				result_parts.append(text)
				continue
			if ntype == 8:  # comment
				result_parts.append(f"<!--{props.get('text_content', '')}-->")
				continue
			if ntype == 10:  # doctype
				result_parts.append(f"<!DOCTYPE {props.get('node_name', '')}>")
				continue
			if ntype != 1:  # unknown
				continue

			# Element node
			tag = props.get('tag_name')
			try:
				attrs = json.loads(props.get('attributes', '{}'))
			except json.JSONDecodeError:
				attrs = {}
				
			# Construct f-string HTML assembly dynamically
			attrs_str = "".join([f' {k}="{str(v).replace("\"", "&quot;")}"' for k, v in attrs.items()])
			result_parts.append(f"<{tag}{attrs_str}>")

			# Void elements have no children or closing tag
			if tag in void_elements:
				continue

			# Push exit marker after children
			stack.append((node_id, 'exit'))

			# Get children for this node natively via the mapped dictionary
			node_children = children.get(node_id, {})
			shadow_ids = node_children.get('shadow', [])
			light_ids = node_children.get('light', [])
				
			# Because it's a stack (LIFO), we push in reverse order of execution:
			# Execution order: 1. shadow wrapper open, 2. shadow children, 3. shadow wrapper close, 4. light children
			# Push order: 4. light children, 3. shadow wrapper close, 2. shadow children, 1. shadow wrapper open
			
			# 4. Light children
			for child_id in reversed(light_ids):
				stack.append((child_id, 'enter'))
				
			# 3, 2, 1. Shadow children and wrappers
			if shadow_ids:
				stack.append(("</template>",)) # 3
				for child_id in reversed(shadow_ids): # 2
					stack.append((child_id, 'enter'))
				stack.append(('<template shadowrootmode="open">',)) # 1

		return ''.join(result_parts)

	def _dom_node_signature(self, node_dict: dict) -> str:
		"""Create a unique signature for a DOM node."""
		if not node_dict:
			return ""
		parts = [node_dict.get('tagName', node_dict.get('nodeName', ''))]
		if 'id' in node_dict:
			parts.append(f"id:{node_dict['id']}")

		attrs = node_dict.get('attributes', {})
		# Include all data-* attributes (often used for unique identifiers)
		for key in attrs:
			if key.startswith('data-'):
				parts.append(f"{key}:{str(attrs[key])}")
		# Also keep the existing important attributes
		for key in ['href', 'src', 'aria-label']:
			if key in attrs:
				parts.append(f"{key}:{str(attrs[key])}")

		# Add content hash if present
		content_hash = attrs.get('data-content-hash', '')
		if content_hash:
			parts.append(f"ch:{content_hash}")

		if node_dict.get('nodeType') == 3: # text node
			# Longer text snippet to differentiate
			text = node_dict.get('textContent', '')[:200]
			parent_sig = node_dict.get('parentSignature', '')
			if parent_sig:
				parts.append(f"txt:{text}|parent:{parent_sig[:50]}")
			else:
				parts.append(f"txt:{text}")

		return "|".join(parts)

	def _insert_dom_node(self, node_dict: dict, page_url: str, parent_id: str = None,
		is_shadow_child: bool = False) -> str:
		"""
		Recursively traverse a DOM snapshot and queue nodes/edges for batch insertion.
		Returns the root node id.
		"""
		node_type = node_dict.get('nodeType')
		# Deterministic node_id: page_url + signature (no random hash)
		node_id = f"{page_url}:{self._dom_node_signature(node_dict)}"

		# Prepare node properties (excluding primary key for SET later)
		props = {
			'node_id': node_id,
			'node_type': node_type,
			'page_url': page_url,
			'signature': self._dom_node_signature(node_dict),
			'content_hash': node_dict.get('attributes', {}).get('data-content-hash', ''),
			'layout_x': node_dict.get('layout_x', 0.0),
			'layout_y': node_dict.get('layout_y', 0.0),
			'layout_z': node_dict.get('layout_z', 0.0),
			'xpath': node_dict.get('xpath', ''),
			'depth': node_dict.get('depth', 0),
			'tag': node_dict.get('tag', ''),
			'is_user_labeled': False,
			'label': ''
		}
		if node_type == 1: # element
			props['tag_name'] = node_dict.get('tagName', '').lower()
			props['node_name'] = node_dict.get('nodeName', '')
			props['id_attr'] = node_dict.get('id', '')
			props['class_name'] = node_dict.get('className', '')
			props['attributes'] = json.dumps(node_dict.get('attributes', {}))
			props['html_raw'] = node_dict.get('outerHTML', '')[:200]
		elif node_type == 3: # text
			props['text_content'] = node_dict.get('textContent', '')
			props['node_name'] = '#text'
		elif node_type == 8: # comment
			props['text_content'] = node_dict.get('nodeValue', '')
			props['node_name'] = '#comment'
		elif node_type == 10: # doctype
			props['node_name'] = node_dict.get('name', '')

		# Queue the node for insertion
		self._batch_nodes.append(props)

		# Queue the parent relationship if any
		if parent_id:
			self._batch_edges.append({
				'from': parent_id,
				'to': node_id,
				'type': 'HAS_SHADOW_ROOT' if is_shadow_child else 'PARENT_OF'
			})
			# Also bridge standard GUI tree structural relationships exclusively
			if not is_shadow_child:
				self._batch_edges.append({
					'from': node_id,
					'to': parent_id,
					'type': 'ChildOf'
				})

		# Process children (light DOM)
		for child in node_dict.get('children', []):
			self._insert_dom_node(child, page_url, parent_id=node_id, is_shadow_child=False)

		# Process shadow root children if present
		shadow = node_dict.get('shadowRoot')
		if shadow:
			for s_child in shadow.get('children', []):
				self._insert_dom_node(s_child, page_url, parent_id=node_id, is_shadow_child=True)

		return node_id

	def _flush_dom_batch(self):
		"""Insert all queued DOM nodes and edges using a single transaction."""
		print(f"\n[RAG-DB Debug] >>> Flushing batched components to Master Graph! [Nodes: {len(self._batch_nodes)}] [Edges: {len(self._batch_edges)}]")
		if not self._batch_nodes:
			print("[RAG-DB Debug] >>> Aborting transaction cleanly natively (No newly deduplicated nodes generated).")
			return

		print("[RAG-DB Debug] >>> Executing native BEGIN TRANSACTION natively...")
		conn = self._get_conn()
		transaction_active = False
		try:
			conn.execute("BEGIN TRANSACTION")
			transaction_active = True

			# All possible columns (excluding node_id, which is used in MERGE)
			node_columns = [
				'node_type', 'page_url', 'signature', 'content_hash',
				'tag_name', 'node_name', 'id_attr', 'class_name',
				'attributes', 'text_content', 'layout_x', 'layout_y', 'layout_z',
				'xpath', 'depth', 'tag', 'is_user_labeled', 'label', 'html_raw'
			]

			# Use MERGE to avoid duplicate key errors
			set_clause = ", ".join([f"n.{col} = row.{col}" for col in node_columns])
			node_query = f"""
				UNWIND $nodes AS row
				MERGE (n:DomNode {{node_id: row.node_id}})
				SET {set_clause}
			"""
			nodes_param = []
			for props in self._batch_nodes:
				row = {'node_id': props['node_id']}
				for col in node_columns:
					row[col] = props.get(col)
				nodes_param.append(row)
			conn.execute(node_query, {'nodes': nodes_param})

			# Batch edges by type
			for rel_type in ['PARENT_OF', 'HAS_SHADOW_ROOT', 'ChildOf']:
				edges_of_type = [e for e in self._batch_edges if e['type'] == rel_type]
				if not edges_of_type:
					continue
				edge_query = f"""
					UNWIND $edges AS edge
					MATCH (a:DomNode {{node_id: edge.from}}), (b:DomNode {{node_id: edge.to}})
					CREATE (a)-[:{rel_type}]->(b)
				"""
				conn.execute(edge_query, {'edges': [{'from': e['from'], 'to': e['to']} for e in edges_of_type]})

			print(f"[RAG-DB Debug] >>> Locking logical structural pointers across mapping... (COMMITTING)")
			conn.execute("COMMIT")
			transaction_active = False
			logger.info(f"Flushed {len(self._batch_nodes)} DOM nodes and {len(self._batch_edges)} edges.")
			print("[RAG-DB Debug] >>> MASTER COMMIT SUCCEEDED!")

		except Exception as e:
			print(f"[RAG-DB Debug] >>> MERGE/CREATE BATCH TRANSACTION CRASHED FATALLY: {e}")
			logger.error(f"DOM batch insertion failed: {e}")
			if transaction_active:
				try:
					conn.execute("ROLLBACK")
				except Exception as rb_e:
					logger.warning(f"Rollback failed: {rb_e}")
			raise
		finally:
			self._batch_nodes.clear()
			self._batch_edges.clear()

	# ------------------------------------------------------------------
	# Prompt Tracking
	# ------------------------------------------------------------------

	def create_prompt(self, prompt_text: str) -> str:
		"""Create a Prompt node and return its ID."""
		self.initialize()
		conn = self._get_conn()
		ts = time.strftime('%Y-%m-%dT%H:%M:%S')
		prompt_id = f"prompt:{compute_content_hash(prompt_text)}:{int(time.time())}"
		try:
			conn.execute(
				"MERGE (p:Prompt {prompt_id: $pid, prompt_text: $pt, timestamp: $ts})",
				{'pid': prompt_id, 'pt': prompt_text[:500], 'ts': ts}
			)
		except Exception as e:
			logger.error(f"Prompt creation error: {e}")
		return prompt_id

	def link_url_to_prompt(self, url: str, prompt_id: str):
		"""Link a Page to a Prompt (for multi-URL session tracking)."""
		self.initialize()
		conn = self._get_conn()
		try:
			conn.execute("""
				MATCH (pg:Page), (pr:Prompt)
				WHERE pg.url = $url AND pr.prompt_id = $pid
				MERGE (pg)-[:LINKED_TO_PROMPT]->(pr)
			""", {'url': url, 'pid': prompt_id})
		except Exception as e:
			logger.error(f"Prompt linking error: {e}")

	def get_urls_for_prompt(self, prompt_id: str) -> List[str]:
		"""Get all URLs linked to a prompt."""
		self.initialize()
		conn = self._get_conn()
		try:
			res = conn.execute("""
				MATCH (pg:Page)-[:LINKED_TO_PROMPT]->(pr:Prompt)
				WHERE pr.prompt_id = $pid RETURN pg.url
			""", {'pid': prompt_id})
			return [r[0] for r in self._iter_results(res)]
		except Exception:
			return []

	# ------------------------------------------------------------------
	# Detected Field Caching (Search / Pagination)
	# ------------------------------------------------------------------
	def cache_detected_field(self, url: str, field_type: str, selector: str):
		"""Cache a detected search field or pagination button for a URL."""
		self.initialize()
		conn = self._get_conn()
		field_id = f"{url}:{field_type}:{compute_content_hash(selector)}"
		try:
			conn.execute("""
				MERGE (df:DetectedField {field_id: $fid, field_type: $ft,
				selector: $sel, url: $url})
			""", {'fid': field_id, 'ft': field_type, 'sel': selector, 'url': url})
			conn.execute("""
				MATCH (pg:Page), (df:DetectedField)
				WHERE pg.url = $url AND df.field_id = $fid
				MERGE (pg)-[:HAS_DETECTED_FIELD]->(df)
			""", {'url': url, 'fid': field_id})
		except Exception as e:
			logger.error(f"Field caching error: {e}")

	def get_cached_fields(self, url: str, field_type: str = None) -> List[Dict]:
		"""Retrieve cached detected fields for a URL."""
		self.initialize()
		conn = self._get_conn()
		try:
			if field_type:
				res = conn.execute("""
					MATCH (pg:Page)-[:HAS_DETECTED_FIELD]->(df:DetectedField)
					WHERE pg.url = $url AND df.field_type = $ft
					RETURN df.selector, df.field_type, df.field_id
				""", {'url': url, 'ft': field_type})
			else:
				res = conn.execute("""
					MATCH (pg:Page)-[:HAS_DETECTED_FIELD]->(df:DetectedField)
					WHERE pg.url = $url
					RETURN df.selector, df.field_type, df.field_id
				""", {'url': url})
			return [{'selector': r[0], 'field_type': r[1], 'field_id': r[2]}
				for r in self._iter_results(res)]
		except Exception:
			return []

	# ------------------------------------------------------------------
	# URL Decomposition
	# ------------------------------------------------------------------

	def index_url_tree(self, url: str):
		"""Decompose URL and store path segments as a linked graph."""
		self.initialize()
		conn = self._get_conn()
		segments = decompose_url(url)
		prev_fp = None

		for seg_data in segments:
			fp = seg_data['full_path']
			seg = seg_data['segment']
			try:
				conn.execute(
					"MERGE (u:UrlPath {segment: $seg, full_path: $fp})",
					{'seg': seg, 'fp': fp}
				)
			except Exception:
				pass

			if prev_fp is None:
				try:
					conn.execute("""
						MATCH (p:Page), (u:UrlPath)
						WHERE p.url = $url AND u.full_path = $fp
						MERGE (p)-[:HAS_PATH_ROOT]->(u)
					""", {'url': url, 'fp': fp})
				except Exception:
					pass
			else:
				try:
					conn.execute("""
						MATCH (u1:UrlPath), (u2:UrlPath)
						WHERE u1.full_path = $fp1 AND u2.full_path = $fp2
						MERGE (u1)-[:NEXT_SEGMENT]->(u2)
					""", {'fp1': prev_fp, 'fp2': fp})
				except Exception:
					pass
			prev_fp = fp

	# ------------------------------------------------------------------
	# Main Indexing (with alt-text and dedup)
	# ------------------------------------------------------------------
	def index_page_state(self, url: str, chunks: List[Dict], prompt_id: str = None) -> Dict:
		"""Index a page state into the graph with proper sample embedding."""
		self.initialize()
		conn = self._get_conn()
		ts = time.strftime('%Y-%m-%dT%H:%M:%S')
		domain = urlparse(url).netloc

		# 1. Create Page node
		try:
			conn.execute(
				"MERGE (p:Page {url: $url, domain: $dom, timestamp: $ts})",
				{'url': url, 'dom': domain, 'ts': ts}
			)
			self.index_url_tree(url)
		except Exception as e:
			logger.error(f"Page merge error: {e}")

		# 2. Link to prompt if provided
		if prompt_id:
			self.link_url_to_prompt(url, prompt_id)

		stats = {'chunks': 0, 'samples': 0, 'embedded': 0, 'skipped_dedup': 0}

		# Collect all texts for batch embedding
		all_texts = []
		text_samples = [] # List of (chunk_id_str, sample_data, sample_idx)

		for chunk_idx, chunk in enumerate(chunks):
			# Extract chunk data
			cid = chunk.get('chunk_id', 0)
			cid_str = f"{url}#{cid}"
			selectors = chunk.get('selectors', [])
			stem = selectors[0] if selectors else "unknown"

			# Determine content types
			ctypes = chunk.get('content_types', [])
			is_input = 'input' in ctypes
			is_button = 'button' in ctypes
			is_text = 'text' in ctypes
			is_link = 'link' in ctypes
			has_structure = 'structure' in ctypes

			# Store Chunk node
			try:
				conn.execute("""
					MERGE (c:Chunk {chunk_id_str: $cid, stem_selector: $stem,
						frequency: $freq, is_input: $hi, is_button: $hb, 
						is_text: $ht, is_link: $hl, has_structure: $hs})
				""", {
					'cid': cid_str, 'stem': stem,
					'freq': chunk.get('frequency', 0),
					'hi': is_input, 'hb': is_button, 'ht': is_text,
					'hl': is_link, 'hs': has_structure
				})

				# Link to page
				conn.execute("""
					MATCH (p:Page), (c:Chunk)
					WHERE p.url = $url AND c.chunk_id_str = $cid
					MERGE (p)-[:CONTAINS]->(c)
				""", {'url': url, 'cid': cid_str})

				stats['chunks'] += 1

			except Exception as e:
				logger.error(f"Chunk insert error: {e}")

			# Collect samples for embedding
			flat_samples = normalize_chunk_samples(chunk)
			for sample_idx, sample in enumerate(flat_samples):
				if not isinstance(sample, dict):
					continue

				text = extract_embeddable_text(sample)
				if text and len(text.strip()) >= 3: # Minimum text length
					all_texts.append(text)
					text_samples.append((cid_str, sample, sample_idx, text))

		# Batch embed all texts
		if all_texts:
			try:
				embeddings = self.embedder.embed_texts(all_texts)

				# Create Sample nodes with embeddings
				for idx, (cid_str, sample, sample_idx, text) in enumerate(text_samples):
					if idx >= len(embeddings):
						break

					sample_id = f"{cid_str}:s{sample_idx}"
					content_hash = compute_content_hash(text)
					has_alt = bool(sample.get('alt', '').strip())

					# Check if sample already exists (deduplication)
					existing = conn.execute(
						"MATCH (s:Sample {content_hash: $hash}) RETURN s.sample_id LIMIT 1",
						{'hash': content_hash}
					)

					if self._iter_results(existing):
						# Sample already exists, just link it
						conn.execute("""
							MATCH (c:Chunk), (s:Sample)
							WHERE c.chunk_id_str = $cid AND s.content_hash = $hash
							MERGE (c)-[:HAS_SAMPLE]->(s)
						""", {'cid': cid_str, 'hash': content_hash})
						stats['skipped_dedup'] += 1
					else:
						# Create new sample with embedding
						conn.execute("""
							MERGE (s:Sample {sample_id: $sid})
							SET s.content = $content,
								s.is_text = true,
								s.has_alt = $has_alt,
								s.content_hash = $hash,
								s.embedding = $embedding
						""", {
							'sid': sample_id,
							'content': text[:1000],
							'has_alt': has_alt,
							'hash': content_hash,
							'embedding': embeddings[idx].tolist()
						})

						# Link to chunk
						conn.execute("""
							MATCH (c:Chunk), (s:Sample)
							WHERE c.chunk_id_str = $cid AND s.sample_id = $sid
							MERGE (c)-[:HAS_SAMPLE]->(s)
						""", {'cid': cid_str, 'sid': sample_id})

						stats['samples'] += 1
						stats['embedded'] += 1

			except Exception as e:
				logger.error(f"Batch embedding failed: {e}")
				# Fallback: create samples without embeddings
				for cid_str, sample, sample_idx, text in text_samples:
					sample_id = f"{cid_str}:s{sample_idx}"
					has_alt = bool(sample.get('alt', '').strip())

					conn.execute("""
						MERGE (s:Sample {sample_id: $sid})
						SET s.content = $content,
							s.is_text = true,
							s.has_alt = $has_alt
					""", {
						'sid': sample_id,
						'content': text[:1000],
						'has_alt': has_alt
					})

					conn.execute("""
						MATCH (c:Chunk), (s:Sample)
						WHERE c.chunk_id_str = $cid AND s.sample_id = $sid
						MERGE (c)-[:HAS_SAMPLE]->(s)
					""", {'cid': cid_str, 'sid': sample_id})

					stats['samples'] += 1

		return stats


	def query_semantic(self, query: str, url: str = None, top_k: int = 5) -> List[Dict]:
		"""Semantic search over embeddings using cosine similarity."""
		self.initialize()

		if not query or not query.strip():
			return []

		try:
			# Embed the query
			query_embedding = self.embedder.embed_query(query)
			query_norm = np.linalg.norm(query_embedding)

			if query_norm == 0:
				return []

			conn = self._get_conn()

			# Build the query based on URL filter
			if url:
				query_sql = """
					MATCH (p:Page)-[:CONTAINS]->(c:Chunk)-[:HAS_SAMPLE]->(s:Sample)
					WHERE p.url = $url AND s.embedding IS NOT NULL
					RETURN s.sample_id, s.content, s.embedding, c.stem_selector, c.chunk_id_str
				"""
				params = {'url': url}
			else:
				# FIX: Join through Chunk to get real chunk_id_str and selector
				query_sql = """
					MATCH (c:Chunk)-[:HAS_SAMPLE]->(s:Sample)
					WHERE s.embedding IS NOT NULL
					RETURN s.sample_id, s.content, s.embedding, c.stem_selector, c.chunk_id_str
				"""
				params = {}

			results = []
			try:
				res = conn.execute(query_sql, params)
				rows = self._iter_results(res)

				for row in rows:
					sample_id, content, embedding, selector, chunk_id_str = row

					# Convert embedding list to numpy array
					if isinstance(embedding, list):
						embedding_array = np.array(embedding, dtype=np.float32)
					else:
						continue

					# Compute cosine similarity
					if np.linalg.norm(embedding_array) == 0:
						similarity = 0.0
					else:
						similarity = float(np.dot(query_embedding, embedding_array) / 
							(query_norm * np.linalg.norm(embedding_array)))

					results.append({
						'sample_id': sample_id,
						'content': content,
						'score': similarity,
						'selector': selector or '',
						'chunk_id': chunk_id_str or sample_id.split(':')[0] if ':' in sample_id else '',
					})

				# Sort by similarity score descending
				results.sort(key=lambda x: x['score'], reverse=True)

				# Return top_k results
				return results[:top_k]

			except Exception as e:
				logger.error(f"Query execution failed: {e}")
				return []

		except Exception as e:
			logger.error(f"Query semantic failed: {e}")
			return []


	def query_semantic_by_prompt(self, prompt_id: str, query: str,
		top_k: int = 100) -> List[Dict]:
		"""Semantic search scoped to ALL prompt URLs with GLOBAL ranking."""
		urls = self.get_urls_for_prompt(prompt_id)

		if not urls:
			logger.warning(f"No URLs found for prompt {prompt_id}")
			return []

		logger.info(f"GLOBAL query for prompt {prompt_id}: searching {len(urls)} URLs")

		all_results = []
		query_embedding = self.embedder.embed_query(query)
		query_norm = np.linalg.norm(query_embedding)

		if query_norm == 0:
			return []

		# Query ALL URLs and combine results
		for url in urls:
			try:
				conn = self._get_conn()

				res = conn.execute("""
					MATCH (p:Page)-[:CONTAINS]->(c:Chunk)-[:HAS_SAMPLE]->(s:Sample)
					WHERE p.url = $url AND s.embedding IS NOT NULL
					RETURN s.sample_id, s.content, s.embedding, p.url, c.chunk_id_str
				""", {'url': url})

				rows = self._iter_results(res)

				for row in rows:
					sample_id, content, embedding, page_url, chunk_id_str = row

					# Compute similarity
					if isinstance(embedding, list):
						embedding_array = np.array(embedding, dtype=np.float32)
						emb_norm = np.linalg.norm(embedding_array)
						if emb_norm == 0:
							similarity = 0.0
						else:
							similarity = float(np.dot(query_embedding, embedding_array) / 
								(query_norm * emb_norm))

						all_results.append({
							'sample_id': sample_id,
							'content': content,
							'score': similarity,
							'url': page_url,
							'chunk_id': chunk_id_str,
						})

			except Exception as e:
				logger.error(f"Query for URL {url} failed: {e}")

		# Sort GLOBALLY by score
		all_results.sort(key=lambda x: x['score'], reverse=True)

		# Return top_k results
		return all_results[:top_k]

	# ------------------------------------------------------------------
	# Category Endpoints
	# ------------------------------------------------------------------
	def get_inputs(self, url: str) -> List[Dict]:
		return self._categorical_query(url, "is_input", True)

	def get_buttons(self, url: str) -> List[Dict]:
		return self._categorical_query(url, "is_button", True)

	def get_text_samples(self, url: str) -> List[Dict]:
		self.initialize()
		conn = self._get_conn()
		try:
			res = conn.execute("""
				MATCH (p:Page)-[:CONTAINS]->(c:Chunk)-[:HAS_SAMPLE]->(s:Sample)
				WHERE p.url = $url AND s.is_text = true
				RETURN c.stem_selector, s.content, s.sample_id
			""", {'url': url})
			return [{'selector': r[0], 'content': r[1], 'sample_id': r[2]}
				for r in self._iter_results(res)]
		except Exception:
			return []

	def get_links(self, url: str) -> List[Dict]:
		return self._categorical_query(url, "is_link", True)

	def get_category_chunks(self, url: str, category) -> List[Dict]:
		flag_map = {
			'input': 'is_input', 'button': 'is_button',
			'text': 'is_text', 'link': 'is_link',
			'url_pattern': 'has_url_pattern',
		}
		cat_key = category.value if hasattr(category, 'value') else str(category)
		flag = flag_map.get(cat_key)
		return self._categorical_query(url, flag, True) if flag else []

	def _categorical_query(self, url: str, flag: str, val: bool) -> List[Dict]:
		self.initialize()
		conn = self._get_conn()
		try:
			res = conn.execute(f"""
				MATCH (p:Page)-[:CONTAINS]->(c:Chunk)
				WHERE p.url = $url AND c.{flag} = $val
				RETURN c.stem_selector, c.chunk_id_str, c.subtree_root, c.frequency
			""", {'url': url, 'val': val})
			return [{'selector': r[0], 'chunk_id': r[1], 'root': r[2], 'frequency': r[3]}
				for r in self._iter_results(res)]
		except Exception:
			return []

	# ------------------------------------------------------------------
	# Action Recording
	# ------------------------------------------------------------------

	def record_action_result(self, chunk_id, url: str,
		action_type: str, success: bool):
		self.initialize()
		conn = self._get_conn()
		ts = time.strftime('%Y-%m-%dT%H:%M:%S')
		cid_str = f"{url}#{chunk_id}" if isinstance(chunk_id, int) else str(chunk_id)
		aid = f"{cid_str}:{action_type}:{int(time.time())}"
		try:
			conn.execute("""
				MERGE (a:Action {action_id: $aid, action_type: $at,
					success: $s, timestamp: $ts})
			""", {'aid': aid, 'at': action_type, 's': success, 'ts': ts})
			try:
				conn.execute("""
					MATCH (c:Chunk), (a:Action)
					WHERE c.chunk_id_str = $cid AND a.action_id = $aid
					MERGE (c)-[:WAS_USED_FOR]->(a)
				""", {'cid': cid_str, 'aid': aid})
			except Exception:
				pass
			try:
				conn.execute("""
					MATCH (p:Page), (a:Action)
					WHERE p.url = $url AND a.action_id = $aid
					MERGE (p)-[:HAS_ACTION]->(a)
				""", {'url': url, 'aid': aid})
			except Exception:
				pass
		except Exception as e:
			logger.error(f"Action recording failed: {e}")

	def get_rag_context(self, query: str, selectors: List[str] = None,
		top_k: int = 3) -> str:
		results = self.query_semantic(query, top_k=top_k)
		if not results:
			return ""
		lines = [f"  {i+1}. [{r['score']:.0%}] {r['selector'][:60]}"
			for i, r in enumerate(results)]
		return f"[RAG Context: {len(results)} matches]\n" + "\n".join(lines)

	# ------------------------------------------------------------------
	# Utilities
	# ------------------------------------------------------------------
	@staticmethod
	def _extract_url_patterns(links: List[str]) -> List[str]:
		patterns = set()
		for link in links:
			if not link or link.startswith('#') or link.startswith('javascript'):
				continue
			p = re.sub(r'\d+', r'\\d+', link)
			p = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
				r'[UUID]', p)
			if p != link:
				patterns.add(p)
		return list(patterns)

	def _iter_results(self, result):
		rows = []
		try:
			while result.has_next():
				rows.append(result.get_next())
		except Exception:
			pass
		return rows

	def _embed_texts(self, texts: List[str]) -> np.ndarray:
		"""Embed texts with proper preprocessing."""
		if not texts:
			return np.zeros((0, NOMIC_EMBED_DIM), dtype=np.float32)
		# Clean texts
		cleaned_texts = []
		for text in texts:
			if not text or not isinstance(text, str):
				continue
			cleaned = clean_text_for_embedding(text)
			if cleaned and len(cleaned) >= 3: # Minimum length for embedding
				# Truncate to max length
				cleaned_texts.append(cleaned[:MAX_EMBED_TEXT_LEN])
		if not cleaned_texts:
			return np.zeros((0, NOMIC_EMBED_DIM), dtype=np.float32)
		# Use Nomic embedder
		if hasattr(self.embedder, 'embed_texts'):
			try:
				embeddings = self.embedder.embed_texts(cleaned_texts)
				if embeddings is not None and len(embeddings) > 0:
					return embeddings
			except Exception as e:
				logger.error(f"Embedding failed: {e}")
				embeddings = None

		return embeddings

	def clear(self):
		import shutil
		if self.db_path.exists():
			shutil.rmtree(self.db_path)
			self._db = None
			self._initialized = False
			self._sample_hash_cache.clear()