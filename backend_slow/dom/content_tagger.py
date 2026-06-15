"""
content_tagger.py — Comprehensive DOM content detection and xpath extraction.

Given a ShadowDOM object, scans every node and every attribute value for:
  - URLs (internal, external, resource/data)
  - Media links (image, video, audio, archive) embedded as substrings
  - Human-readable text (visible, accessible, metadata)
  - Interactive elements (inputs, buttons, forms)
  - Embedded JSON (ld+json, data-* attrs, inline script blocks)

Returns categorized arrays of absolute xpaths.
"""

from __future__ import annotations

import re
import json as _json
import html
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field

try:
	from .shadow_html_parser import ShadowDOM, ShadowNode, get_absolute_xpath
except ImportError:
	from shadow_html_parser import ShadowDOM, ShadowNode, get_absolute_xpath


# ---------------------------------------------------------------------------
# Regex patterns — compiled once, reused across all calls
# ---------------------------------------------------------------------------

# URL detection: matches anything that looks like a URL embedded as a substring
# Covers http(s), protocol-relative, absolute paths, data URIs, blob URIs
_URL_PATTERN = re.compile(
	r"""(?:
	     https?://[^\s"'<>(){}\[\]]+            # http or https
	   | //[^\s"'<>(){}\[\]]+                    # protocol-relative
	   | data:[a-zA-Z0-9+/\.-]+;[^\s"'<>]+      # data URI
	   | blob:[^\s"'<>]+                         # blob URI
	   | /[a-zA-Z0-9_.~:/?#@!$&'()*+,;=%-]+     # absolute path (starts with /)
	 )""",
	re.VERBOSE,
)

_CSS_URL_PATTERN = re.compile(r'''url\s*\(\s*['"]?([^'"\)]+)['"]?\s*\)''', re.IGNORECASE)

# Media file extensions — each category as a frozenset for O(1) lookup
_IMAGE_EXTS = frozenset({
	'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.avif',
	'.bmp', '.tiff', '.tif', '.apng', '.jfif', '.pjpeg', '.pjp',
})
_VIDEO_EXTS = frozenset({
	'.mp4', '.webm', '.ogg', '.ogv', '.mov', '.avi', '.mkv', '.flv',
	'.wmv', '.m4v', '.3gp', '.ts', '.m3u8',
})
_AUDIO_EXTS = frozenset({
	'.mp3', '.wav', '.flac', '.ogg', '.oga', '.aac', '.wma', '.opus',
	'.m4a', '.mid', '.midi',
})
_ARCHIVE_EXTS = frozenset({
	'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tar.gz',
	'.tar.bz2', '.tar.xz', '.tgz', '.cab', '.iso', '.dmg',
})

_ALL_MEDIA_EXTS = _IMAGE_EXTS | _VIDEO_EXTS | _AUDIO_EXTS | _ARCHIVE_EXTS

# Extension extraction from a URL-like string
_EXT_PATTERN = re.compile(r'\.([a-zA-Z0-9]{2,5})(?:[?#]|$)')

# Attributes known to carry human-readable text
_TEXT_ATTRS = frozenset({
	'alt', 'title', 'placeholder', 'aria-label', 'aria-labelledby',
	'aria-describedby', 'aria-description', 'aria-placeholder',
	'aria-valuetext', 'aria-roledescription', 'aria-errormessage',
	'label', 'summary', 'caption', 'abbr', 'acronym',
})

# Metadata text attributes (less visible but still content).
# ``datetime`` (ISO-8601 on <time>, <ins>, <del>) carries machine-
# parseable content that's still valuable for retrieval — without it
# the only trace of a ``<time datetime="2024-03-15">Published last
# week</time>`` in the embedding stream was the noisy surface text.
# We intentionally do NOT include ``value`` here: it's a form-input
# key on <input>/<option>/<button> and would fold CSRF tokens, hidden
# IDs, and form keys into the embedding.
_META_TEXT_ATTRS = frozenset({
	'content', 'data-tooltip', 'data-title', 'data-caption',
	'data-description', 'data-alt', 'data-label', 'data-placeholder',
	'data-text', 'data-name', 'data-value',
	'datetime',
})

# Interactive element tags
_INPUT_TAGS = frozenset({
	'input', 'textarea', 'select', 'option', 'optgroup', 'datalist',
	'output', 'progress', 'meter',
})
_BUTTON_TAGS = frozenset({'button'})
_FORM_TAGS = frozenset({'form', 'fieldset', 'legend', 'label'})

# Interactive roles (WAI-ARIA)
_INTERACTIVE_ROLES = frozenset({
	'button', 'checkbox', 'combobox', 'grid', 'gridcell', 'link',
	'listbox', 'menu', 'menubar', 'menuitem', 'menuitemcheckbox',
	'menuitemradio', 'option', 'radio', 'radiogroup', 'searchbox',
	'slider', 'spinbutton', 'switch', 'tab', 'tablist', 'textbox',
	'tree', 'treegrid', 'treeitem',
})

# Tags that signal embedded JSON or structured data
_JSON_SCRIPT_TYPES = frozenset({
	'application/ld+json', 'application/json', 'importmap',
})

# JSON-like heuristic pattern for attribute values
_JSON_HEURISTIC = re.compile(r'^\s*[\[{]')

# Attributes to skip entirely (styling, dimensions, structural, implementation)
_SKIP_ATTRS = frozenset({
	# CSS / Styling
	'style', 'class', 'width', 'height',
	# SVG drawing attributes
	'viewbox', 'xmlns', 'xmlns:xlink', 'xmlns:svg', 'version',
	'd', 'points', 'transform', 'fill', 'stroke', 'clip-path',
	'stroke-width', 'stroke-linecap', 'stroke-linejoin',
	'fill-rule', 'clip-rule', 'opacity', 'filter',
	# Structural / identity attributes (never content)
	'id', 'name', 'for', 'type', 'method', 'enctype', 'target',
	'tabindex', 'dir', 'lang', 'translate', 'slot', 'is',
	'autocomplete', 'autocorrect', 'autocapitalize', 'spellcheck',
	# ARIA state/relationship attributes (boolean/id-ref, not text)
	'aria-controls', 'aria-owns', 'aria-flowto', 'aria-activedescendant',
	'aria-expanded', 'aria-haspopup', 'aria-hidden', 'aria-disabled',
	'aria-selected', 'aria-checked', 'aria-pressed', 'aria-live',
	'aria-atomic', 'aria-relevant', 'aria-busy', 'aria-current',
	'aria-modal', 'aria-multiline', 'aria-multiselectable',
	'aria-orientation', 'aria-readonly', 'aria-required', 'aria-sort',
	'aria-invalid', 'aria-level', 'aria-colcount', 'aria-colindex',
	'aria-colspan', 'aria-rowcount', 'aria-rowindex', 'aria-rowspan',
	'aria-setsize', 'aria-posinset', 'aria-valuemin', 'aria-valuemax',
	'aria-valuenow',
	# Framework / test / automation IDs (never content)
	'data-testid', 'data-cy', 'data-qa', 'data-automation-id',
	'data-component', 'data-reactid',
})

# Tags that do not break a text block's flow.
_INLINE_TAGS = frozenset({
	"a", "abbr", "b", "bdi", "bdo", "br", "cite", "code", "data", "dfn",
	"em", "i", "kbd", "mark", "q", "rp", "rt", "ruby", "s", "samp",
	"small", "span", "strong", "sub", "sup", "time", "u", "var", "wbr",
	"img", "svg", "picture", "canvas", "video", "audio"
})

# Prefixes for attribute names to skip entirely — catches variants like
# data-testid-*, data-cy-*, data-reactid-*, etc.
_SKIP_ATTR_PREFIXES = (
	'data-testid', 'data-cy-', 'data-qa-', 'data-automation',
	'data-react', 'data-radix', 'data-state', 'data-orientation',
	'data-side', 'data-align', 'data-disabled',
)


# ---------------------------------------------------------------------------
# Data classes for tagged results
# ---------------------------------------------------------------------------

@dataclass
class ContentTag:
	"""A single piece of detected content at a specific xpath."""
	xpath: str
	category: str # 'url', 'media', 'text', 'interactive', 'json'
	subcategory: str # e.g. 'image', 'accessible', 'input', 'ld_json'
	value: str # the extracted value
	source_attr: str # which attribute it came from ('' for text nodes)


@dataclass
class TaggedContent:
	"""Complete categorized extraction result for a DOM snapshot."""
	urls: Dict[str, List[str]] = field(default_factory=lambda: {
		'internal': [], 'external': [], 'resource': [],
	})
	media: Dict[str, List[str]] = field(default_factory=lambda: {
		'images': [], 'video': [], 'audio': [], 'archives': [],
	})
	text: Dict[str, List[str]] = field(default_factory=lambda: {
		'visible': [], 'accessible': [], 'metadata': [],
	})
	interactive: Dict[str, List[str]] = field(default_factory=lambda: {
		'inputs': [], 'buttons': [], 'links': [], 'forms': [],
		'event_handlers': [],
	})
	json_data: Dict[str, List[str]] = field(default_factory=lambda: {
		'ld_json': [], 'data_attrs': [], 'inline': [],
	})

	# Flat list of all individual tags for detailed access
	all_tags: List[ContentTag] = field(default_factory=list)

	def all_content_xpaths(self) -> Set[str]:
		"""Return the union of all xpaths across every category."""
		xpaths = set()
		for group in (self.urls, self.media, self.text,
			self.interactive, self.json_data):
			for arr in group.values():
				xpaths.update(arr)
		return xpaths


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _classify_url(url: str) -> str:
	"""Classify a URL as internal, external, or resource."""
	stripped = url.strip()
	if stripped.startswith('data:') or stripped.startswith('blob:'):
		return 'resource'
	if stripped.startswith('//') or stripped.startswith('http'):
		return 'external'
	# Absolute path — treat as internal
	return 'internal'


def _classify_media(url: str) -> Optional[str]:
	"""Return media subcategory if URL ends with a known media extension."""
	if url.startswith('data:image/'):
		return 'images'
	if url.startswith('data:video/'):
		return 'video'
	if url.startswith('data:audio/'):
		return 'audio'

	# Strip query/fragment and check extension
	clean = url.split('?')[0].split('#')[0].lower()
	m = _EXT_PATTERN.search(clean)
	if not m:
		return None
	ext = '.' + m.group(1)
	if ext in _IMAGE_EXTS:
		return 'images'
	if ext in _VIDEO_EXTS:
		return 'video'
	if ext in _AUDIO_EXTS:
		return 'audio'
	if ext in _ARCHIVE_EXTS:
		return 'archives'
	return None


def _extract_urls_from_value(value: str) -> List[str]:
	"""Extract all URL-like substrings from an arbitrary attribute value."""
	urls = _URL_PATTERN.findall(value)
	valid = []
	for u in urls:
		if u.startswith('/') and not u.startswith('//'):
			# Reject extremely short generic paths unless it is the root
			if len(u) < 2 and u != '/':
			    continue
			# Reject common non-content developer paths that cause massive false positives
			if any(junk in u.lower() for junk in ['/track', '/log', '/ping', '/chunk', '/static/', '/wp-json/', '/api/']):
				continue
		valid.append(u)
	return valid


def _looks_like_json(value: str) -> bool:
	"""Heuristic check if a string value is likely embedded JSON."""
	if len(value) < 20 or len(value) > 5000: # Ignore tiny IDs and block massive strings from hanging the parser
		return False
	if not _JSON_HEURISTIC.match(value):
		return False
	try:
		_json.loads(value)
		return True
	except (ValueError, TypeError):
		return False

def _has_real_text(text: str) -> bool:
	"""Require at least 1 alphanumeric char to filter out icon fonts and stray punctuation."""
	return any(c.isalnum() for c in text)


# Translation table that strips zero-width / NBSP noise out of visible text.
# Hoisted out of the per-node hot path; ``str.maketrans`` was being rebuilt
# 3× per node (text node, leaf element text, mixed-children text) and on a
# 20K-node page that's 60K table allocations for an unchanging table.
_INVISIBLE_TRANS = str.maketrans('', '', '\u200b\u200c\u200d\ufeff\u00a0')

# URL-attribute whitelist — used when extracting URLs from ``href``/``src``-
# style attributes. Frozenset gives O(1) ``in`` checks vs. the previous
# ~13-element tuple ``in`` (linear scan).
_URL_BEARING_ATTRS = frozenset({
	'href', 'src', 'data-src', 'data-lazy-src', 'action', 'formaction',
	'poster', 'data-original', 'data-original-src', 'data-image',
	'data', 'cite', 'longdesc',
})

# Attributes whose values are NEVER worth a generic URL regex sweep —
# they're booleans, ARIA hooks, or pure-text. Letting the URL regex chew
# on every ``aria-label`` / ``placeholder`` / ``alt`` value showed up as
# a measurable hotspot on real pages (avg 5+ attrs/node × 20K nodes).
_NON_URL_ATTR_PREFIXES = ('aria-',)
_NON_URL_ATTRS = frozenset({
	'class', 'id', 'name', 'type', 'role', 'title', 'alt', 'placeholder',
	'value', 'label', 'lang', 'dir', 'tabindex', 'maxlength', 'minlength',
	'min', 'max', 'step', 'pattern', 'autocomplete', 'autocapitalize',
	'autocorrect', 'spellcheck', 'inputmode', 'enterkeyhint', 'rows',
	'cols', 'wrap', 'size', 'multiple', 'readonly', 'required', 'disabled',
	'checked', 'selected', 'hidden', 'draggable', 'contenteditable',
	'translate', 'colspan', 'rowspan', 'headers', 'scope', 'abbr',
	'datetime', 'pubdate', 'reversed', 'start',
})


# ---------------------------------------------------------------------------
# Core tagger
# ---------------------------------------------------------------------------

class ContentTagger:
	"""
	Walks a ShadowDOM tree and extracts all contentful xpaths.
	
	Usage:
	    dom = ShadowDOM(html_string)
	    tagger = ContentTagger(dom)
	    result = tagger.tag()
	    # result.urls['internal'] → list of xpaths
	    # result.all_content_xpaths() → set of all xpaths with content
	"""

	def __init__(self, dom: ShadowDOM, mask: Optional[Set[int]] = None):
		self.dom = dom
		self._result: Optional[TaggedContent] = None
		self._seen_xpaths: Set[str] = set()
		self.mask = mask or set()
		self._skip_text_ids: Set[int] = set()

	def tag(self) -> TaggedContent:
		"""Run the full content extraction pass. Results are cached."""
		if self._result is not None:
			return self._result

		self._result = TaggedContent()
		self._seen_xpaths = set()

		for node in self.dom.iter_all():
			if id(node) in self.mask:
				continue
			self._process_node(node)

		return self._result

	def _process_node(self, node: ShadowNode) -> None:
		"""Classify a single node and all its attribute values."""
		tag = node.tag.lower() if node.tag else ''

		# Skip non-structural nodes
		if tag.startswith('#') and tag not in ('#text', '#comment'):
			return

		xpath = get_absolute_xpath(node)

		# --- 1. Visible text (text nodes) ---
		# DOMAIN_MODEL §4.1: all human-readable text content.
		# Filter: strip whitespace + zero-width chars, require ≥1 alphanumeric.
		if tag == '#text':
			if id(node) not in self._skip_text_ids:
				text_parts = []
				if node.text and node.text.strip(): text_parts.append(node.text.strip())
				if node.tail and node.tail.strip(): text_parts.append(node.tail.strip())
				text = " ".join(text_parts).translate(_INVISIBLE_TRANS).strip()
				if text and _has_real_text(text):
					self._add('text', 'visible', xpath, text, '')
			return

		# --- 2. Interactive elements ---
		# DOMAIN_MODEL §4.1: inputs, textareas, selects, buttons, <a>,
		# forms, role-based, contenteditable, and event-handler elements.
		if tag in _INPUT_TAGS:
			self._add('interactive', 'inputs', xpath, tag, '')
		elif tag in _BUTTON_TAGS:
			self._add('interactive', 'buttons', xpath, tag, '')
		elif tag == 'a':
			self._add('interactive', 'links', xpath, tag, '')
		elif tag in _FORM_TAGS:
			self._add('interactive', 'forms', xpath, tag, '')

		# Check role attribute for interactive
		role = (node.get_attr('role') or '').lower()
		if role in _INTERACTIVE_ROLES:
			subcat = 'buttons' if role == 'button' else 'inputs'
			self._add('interactive', subcat, xpath, f'{tag}[role={role}]', 'role')

		# contenteditable
		if node.get_attr('contenteditable') in ('true', ''):
			self._add('interactive', 'inputs', xpath, f'{tag}[contenteditable]',
				'contenteditable')

		# Event handler attributes (onclick, onsubmit, etc.). Iterate the
		# underlying dict directly — ``get_all_attrs`` returns a fresh copy
		# each call, and on a 24k-node page this hot loop was copying the
		# attribute dict twice per node for a pure read.
		for attr_name in node.attributes:
			if attr_name.lower().startswith('on') and len(attr_name) > 2:
				self._add('interactive', 'event_handlers', xpath,
					f'{tag}[{attr_name}]', attr_name)
				break # One event handler is enough to mark interactive

		# --- 2.5 Media elements ---
		if tag in ('img', 'picture', 'svg', 'canvas'):
			self._add('media', 'images', xpath, tag, '')
		elif tag in ('video', 'source', 'track'):
			self._add('media', 'video', xpath, tag, '')
		elif tag == 'audio':
			self._add('media', 'audio', xpath, tag, '')
		elif tag == 'input':
			# ``<input type="image" src="...">`` is an image-button submit;
			# the ``src`` attribute carries a real image resource URL,
			# same semantics as ``<img>``. Without this branch, the
			# element was only tagged interactive so its image never
			# reached the chunker's media buckets or the frontend's
			# billboard spawner. All other input types (text, checkbox,
			# submit, hidden, ...) remain purely interactive.
			input_type = (node.get_attr('type') or '').lower().strip()
			if input_type == 'image':
				self._add('media', 'images', xpath, tag, '')

		# --- 2.6 <style> blocks: pull out background-image URLs ---
		# Inline ``style="..."`` is already scanned further down via the
		# generic attribute pass, but ``<style>...</style>`` children
		# are CDATA that the HTMLParser hands us as ``.text`` on the
		# style node. Without this pass, stylesheet-declared images
		# (e.g. ``body { background: url(bg.jpg); }``) never enter the
		# media tag stream and the chunker / billboard spawner can't
		# surface them.
		if tag == 'style' and node.text:
			style_text = html.unescape(node.text)
			for u in _CSS_URL_PATTERN.findall(style_text):
				u = u.strip()
				if not u:
					continue
				url_class = _classify_url(u)
				self._add('urls', url_class, xpath, u[:500], 'text()')
				media_cat = _classify_media(u)
				if media_cat:
					self._add('media', media_cat, xpath, u[:500], 'text()')

		# --- 3. Embedded JSON (ld+json scripts) ---
		if tag == 'script':
			script_type = (node.get_attr('type') or '').lower().strip()
			if script_type in _JSON_SCRIPT_TYPES:
				self._add('json_data', 'ld_json', xpath,
					script_type, 'type')

				# Full structured pass: parse the payload (JSON-LD often
				# contains VideoObject / ImageObject / Product schemas
				# with thumbnailUrl / contentUrl / embedUrl / image /
				# logo fields that drive SEO previews). We walk the
				# parsed tree and emit one tag per text field and one
				# per URL-bearing field so the chunker and renderer see
				# them individually instead of a single opaque blob.
				if node.text:
					self._scan_json_ld_payload(node.text, xpath)

					# Even when JSON parsing fails (malformed payload),
					# still run the flat-regex URL sweep so nothing that
					# looks like a media URL slips through.
					found_urls = _extract_urls_from_value(node.text)
					for url in found_urls:
						url_class = _classify_url(url)
						self._add('urls', url_class, xpath, url[:500], 'text()')
						media_cat = _classify_media(url)
						if media_cat:
							self._add('media', media_cat, xpath, url[:500], 'text()')
				return # Don't scan script contents for URLs etc.

		# --- 4. Scan ALL attribute values ---
		# Iterate ``node.attributes`` directly to avoid the per-node dict
		# copy inside ``get_all_attrs``.
		for attr_name, attr_value in node.attributes.items():
			if not isinstance(attr_value, str) or not attr_value.strip():
				continue

			# Avoid blocking the main thread with massive regex searches on base64 images or inline SVGs
			if len(attr_value) > 2000:
				continue

			attr_lower = attr_name.lower()

			# Special check for inline CSS background images
			if attr_lower == 'style':
				style_val = html.unescape(attr_value)
				for u in _CSS_URL_PATTERN.findall(style_val):
					u = u.strip()
					if not u: continue
					url_class = _classify_url(u)
					self._add('urls', url_class, xpath, u[:500], 'style')
					media_cat = _classify_media(u)
					if media_cat:
						self._add('media', media_cat, xpath, u[:500], 'style')

			if attr_lower in _SKIP_ATTRS:
				continue
			# Prefix-based skip for framework/test/state attrs. ``str.startswith``
			# accepts a tuple of prefixes natively at C-speed — faster than a
			# Python-level ``any(...)`` genexpr over the same tuple.
			if attr_lower.startswith(_SKIP_ATTR_PREFIXES):
				continue

			val = attr_value.strip()

			# 4a. Text attributes (accessible, metadata)
			# DOMAIN_MODEL §4.1: "The full set of 20+ text-bearing
			# attributes tracked comprehensively." No length threshold
			# beyond non-empty + has alphanumeric.
			if attr_lower in _TEXT_ATTRS and val and _has_real_text(val):
				self._add('text', 'accessible', xpath, val, attr_name)
			elif attr_lower in _META_TEXT_ATTRS and val and _has_real_text(val):
				self._add('text', 'metadata', xpath, val, attr_name)

			# 4b. JSON embedded in data-* attributes
			if attr_lower.startswith('data-') and _looks_like_json(val):
				self._add('json_data', 'data_attrs', xpath, val, attr_name)
				# We do not `continue` here because embedded JSON often contains
				# valuable CDN image URLs and deep links that we want to extract!

			# 4c. URL extraction
			# ``data`` is <object>'s resource URL (legacy Flash/PDF
			# embed, also used for modern <object type="image/svg+xml"
			# data="...">). ``cite`` points at the source of a quote on
			# <blockquote> and <q>. ``longdesc`` is the long-description
			# URL for <img>/<iframe> (still valid HTML4 and occasionally
			# used by archive.org snapshots). Without these three
			# spellings, those URLs only surfaced if they happened to
			# match the generic URL regex — which missed relative paths
			# that don't start with ``/``.
			found_urls = []
			if attr_lower in _URL_BEARING_ATTRS:
				if not val.lower().startswith(('javascript:', 'mailto:', 'tel:')):
					# ``data`` is only a URL on <object>; on other
					# elements it's rarely a URL and often a text-like
					# value. Gate by tag so we don't mis-tag generic
					# ``data`` attributes as URLs.
					if attr_lower == 'data' and tag != 'object':
						pass
					else:
						found_urls = [val]
			elif attr_lower == 'srcset':
				found_urls = [p.strip().split()[0] for p in val.split(',') if p.strip()]
			elif (
				attr_lower in _NON_URL_ATTRS
				or attr_lower.startswith(_NON_URL_ATTR_PREFIXES)
			):
				# Skip the generic regex sweep for attributes that
				# structurally never carry URLs (ARIA hooks, booleans,
				# size/length/index attributes, etc.). On a real-world
				# page the regex sweep dominated content_tag — rejecting
				# obviously-non-URL attributes by name first lets the
				# remaining catch-all path stay focused on data-* and
				# other extension attrs that occasionally hide URLs.
				pass
			else:
				found_urls = _extract_urls_from_value(val)

			for url in found_urls:
				url_class = _classify_url(url)
				self._add('urls', url_class, xpath, url[:500], attr_name)

				# 4d. Media classification from URL extension
				media_cat = _classify_media(url)
				if media_cat:
					self._add('media', media_cat, xpath, url[:500], attr_name)

		# --- 5. Element-level text (direct .text on element) ---
		# DOMAIN_MODEL §4.1: "All human-readable text content collected
		# from direct text nodes (visible content)."
		# Filter: strip whitespace + zero-width chars, require ≥1 alphanumeric.
		# No tag-dependent length thresholds per the spec.
		if tag not in ('script', 'style') and id(node) not in self._skip_text_ids:
			has_block_children = False
			children = node.get_children(include_shadow=True) if hasattr(node, 'get_children') else getattr(node, 'children', [])
			for child in children:
				ctag = child.tag.lower() if child.tag else ''
				if ctag and not ctag.startswith('#') and ctag not in _INLINE_TAGS:
					has_block_children = True
					break

			if not has_block_children:
				text_parts = []
				text_val = node.get_text(recursive=True, separator=" ")
				if text_val and text_val.strip(): text_parts.append(text_val.strip())
				if node.tail and node.tail.strip(): text_parts.append(node.tail.strip())
				if text_parts:
					final_val = " ".join(text_parts).translate(_INVISIBLE_TRANS).strip()
					if final_val and _has_real_text(final_val):
						self._add('text', 'visible', xpath, final_val, '')
						# Prevent inline children from being tagged individually and duplicating text
						if hasattr(node, 'iter_descendants'):
							for desc in node.iter_descendants():
								self._skip_text_ids.add(id(desc))
			else:
				text_parts = []
				if node.text and node.text.strip(): text_parts.append(node.text.strip())
				if node.tail and node.tail.strip(): text_parts.append(node.tail.strip())
				if text_parts:
					text_val = " ".join(text_parts).translate(_INVISIBLE_TRANS).strip()
					if text_val and _has_real_text(text_val):
						self._add('text', 'visible', xpath, text_val, '')

		# Meta tag content
		if tag == 'meta':
			content = (node.get_attr('content') or '').strip()
			if content:
				self._add('text', 'metadata', xpath, content, 'content')
				# Also scan meta content for URLs
				for url in _extract_urls_from_value(content):
					url_class = _classify_url(url)
					self._add('urls', url_class, xpath, url, 'content')

	# JSON-LD fields whose VALUE is a URL or list of URLs. Schema.org
	# uses ``url``-suffixed keys broadly; we special-case well-known
	# media-bearing ones so the media classifier gets the right
	# subcategory (images vs. video vs. audio) rather than a generic
	# "external URL" tag.
	_JSONLD_IMAGE_FIELDS = frozenset({
		'image', 'logo', 'thumbnail', 'thumbnailurl', 'photo',
		'primaryimageofpage', 'icon',
	})
	_JSONLD_VIDEO_FIELDS = frozenset({
		'contenturl', 'embedurl', 'video', 'trailer',
	})
	_JSONLD_AUDIO_FIELDS = frozenset({'audio'})
	_JSONLD_TEXT_FIELDS = frozenset({
		'name', 'headline', 'description', 'alternatename',
		'abstract', 'articlebody', 'caption', 'disambiguatingdescription',
		'keywords', 'text',
	})

	def _scan_json_ld_payload(self, raw: str, script_xpath: str) -> None:
		"""Parse a ``<script type="application/ld+json">`` body and tag fields.

		Tolerates malformed payloads (returns silently) and nested
		arrays. Each field we recognise is emitted under its best
		category — text fields as ``text/metadata`` with the JSON key
		as ``source_attr``, URL fields as ``urls/*`` plus the matching
		``media/*`` subcategory so the chunker's
		:meth:`_image_url_for_member` / ``extractMediaFromHtml`` pick
		them up alongside direct ``<img>`` / ``<video>`` tags.
		"""
		try:
			payload = _json.loads(raw)
		except (ValueError, TypeError):
			return

		def _emit_url_like(field: str, value: str) -> None:
			val = (value or "").strip()
			if not val:
				return
			url_class = _classify_url(val)
			self._add('urls', url_class, script_xpath, val[:500], f'ld_json:{field}')
			key = field.lower()
			# Explicit-field classification first — covers cases like
			# ``embedUrl`` pointing at a YouTube page URL with no .mp4
			# extension.
			if key in self._JSONLD_IMAGE_FIELDS:
				self._add('media', 'images', script_xpath, val[:500], f'ld_json:{field}')
			elif key in self._JSONLD_VIDEO_FIELDS:
				self._add('media', 'video', script_xpath, val[:500], f'ld_json:{field}')
			elif key in self._JSONLD_AUDIO_FIELDS:
				self._add('media', 'audio', script_xpath, val[:500], f'ld_json:{field}')
			else:
				# Fall back to extension-based classification for
				# generic ``url`` / ``sameAs`` keys so a .jpg URL there
				# still surfaces as an image.
				mcat = _classify_media(val)
				if mcat:
					self._add('media', mcat, script_xpath, val[:500], f'ld_json:{field}')

		def _walk(obj, parent_key: str = "") -> None:
			if isinstance(obj, dict):
				for k, v in obj.items():
					k_str = str(k)
					_walk(v, k_str)
			elif isinstance(obj, list):
				for item in obj:
					_walk(item, parent_key)
			elif isinstance(obj, str):
				key = parent_key.lower()
				# Text-bearing prose fields — emit as metadata so the
				# chunker's text budget sees them.
				if key in self._JSONLD_TEXT_FIELDS and _has_real_text(obj):
					self._add('text', 'metadata', script_xpath, obj[:500], f'ld_json:{parent_key}')
				# URL-bearing fields: heuristic matches either an
				# explicit key name or a URL-like value anywhere.
				if (
					key in self._JSONLD_IMAGE_FIELDS
					or key in self._JSONLD_VIDEO_FIELDS
					or key in self._JSONLD_AUDIO_FIELDS
					or key in ('url', 'sameas', 'mainentityofpage', 'identifier')
					or obj.startswith(('http://', 'https://', '//'))
				):
					_emit_url_like(parent_key, obj)
			# ints/floats/bools/None carry no extractable content.

		_walk(payload)

	def _add(self, category: str, subcategory: str, xpath: str,
		value: str, source_attr: str) -> None:
		"""Register a content finding."""
		tag = ContentTag(
			xpath=xpath,
			category=category,
			subcategory=subcategory,
			value=value,
			source_attr=source_attr,
		)
		self._result.all_tags.append(tag)
		self._seen_xpaths.add(xpath)

		# Add xpath to the right bucket (deduplicate within bucket)
		group = getattr(self._result, category)
		arr = group[subcategory]
		if xpath not in self._seen_xpaths or True:
			# We allow duplicate xpaths across categories but only add
			# to a specific bucket once per xpath
			if xpath not in arr:
				arr.append(xpath)
