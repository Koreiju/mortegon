"""Compile pipeline (Workstream D1; domain anchor §8D.2.1, §8D.20, §8D.30).

The concept-node ``data`` block is a programmable template. The
compile pipeline walks it on every settled cascade and resolves:

  1. Curly-brace ``{slug}`` references against the concept graph
     (the existing ``concept_graph.js`` Compile button already does
     this client-side via ``_compileConceptNode``).
  2. **Cypher query patterns** (§8D.2.1) — strings that look like
     Cypher (``MATCH ... RETURN ...``, ``CALL ...``, ``CREATE ...``)
     are extracted, executed against the unified Database, and the
     result substituted in place. The resolved structure feeds the
     standard recursive decomposition that produces the ``rendering``
     field.
  3. Plain text passes through unchanged.

This module exposes the detection + execution path as a REST
endpoint (``POST /api/compile_pipeline``) so the frontend can
delegate the cypher resolution to the backend rather than
re-implementing the Kuzu connection client-side.

§8D.20 — the ``rendering`` field is a **syntax-free pretty-print**:
keys and values laid out by indentation alone, with tabs and newlines
mimicking the tree, with no curly braces, brackets, colons, or other
syntactic punctuation. ``compute_rendering_tree`` derives it from the
``data`` template: resolve ``{slug}`` refs against the concept graph;
parse JSON-shaped output if applicable; emit a syntax-stripped
indented tree. Plain text falls through unchanged.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Cypher pattern detection
# ---------------------------------------------------------------------------

# Heuristic: a fragment is a cypher query if (a) it's tagged with a
# ```cypher code fence, OR (b) it begins (after whitespace) with one
# of MATCH / CALL / CREATE / MERGE / RETURN / WITH and contains the
# RETURN keyword.

_CYPHER_FENCE_RE = re.compile(
    r"```\s*cypher\s*\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)

_CYPHER_KEYWORDS = ("MATCH", "CALL", "CREATE", "MERGE", "WITH", "RETURN", "UNWIND")


def _looks_like_cypher(text: str) -> bool:
    """Heuristic: is ``text`` a standalone Cypher statement?

    The §8D.2.1 disambiguation rule is intentionally conservative —
    if you accidentally type 'MATCH' in prose it would not be
    extracted unless the whole fragment starts with it and contains
    ``RETURN``. Stricter than necessary on purpose; user can always
    use the code-fence form to be explicit.
    """
    if not text or len(text) > 4000:
        return False
    stripped = text.strip()
    upper = stripped.upper()
    if not upper.startswith(_CYPHER_KEYWORDS):
        return False
    # Require RETURN somewhere (statements without RETURN are mutation-
    # only — we don't auto-execute those without the explicit fence).
    if "RETURN" not in upper and not upper.startswith(("CREATE ", "MERGE ", "CALL ")):
        return False
    # Require at least one parenthesised pattern OR a colon (label).
    if "(" not in stripped and ":" not in stripped:
        return False
    return True


def detect_cypher_segments(text: str) -> List[Tuple[int, int, str]]:
    """Find Cypher segments in ``text``.

    Returns ``[ (start, end, cypher_text) ]`` covering every detected
    segment. Spans are character offsets so the caller can splice the
    result back in place.

    Two detection paths:
      * Explicit ``` ```cypher ... ``` ``` fences — most reliable.
      * Bare top-level MATCH/CALL/CREATE/MERGE statements when the
        ENTIRE non-whitespace content of the ``text`` looks Cypher-y.
    """
    segments: List[Tuple[int, int, str]] = []
    # Path 1: code-fenced cypher.
    for m in _CYPHER_FENCE_RE.finditer(text):
        cypher = (m.group(1) or "").strip()
        if cypher:
            segments.append((m.start(), m.end(), cypher))
    # Path 2: bare top-level — only if the WHOLE text is one cypher
    # statement (we don't try to find embedded cypher in mixed text
    # because the false-positive cost is too high).
    if not segments and _looks_like_cypher(text):
        segments.append((0, len(text), text.strip()))
    return segments


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_cypher(cypher: str, db_conn=None) -> Dict[str, Any]:
    """Execute a Cypher query against the Kuzu connection.

    Returns ``{ ok: bool, rows: list[list], columns: list[str], error?: str }``.
    Safe-by-default: on any exception, returns ``{ ok: False, error: ... }``
    rather than raising — the compile pipeline catches errors and
    leaves the original cypher text in place if execution fails.
    """
    if db_conn is None:
        try:
            from backend.database import get_connection
            db_conn = get_connection()
        except Exception as e:
            return {"ok": False, "error": f"no DB connection: {e}", "rows": [], "columns": []}
    try:
        res = db_conn.execute(cypher)
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": [], "columns": []}
    # Kuzu's result iterator exposes column names + rows.
    columns: List[str] = []
    try:
        columns = list(res.get_column_names())
    except Exception:
        pass
    rows: List[List[Any]] = []
    try:
        while res.has_next():
            r = res.get_next()
            # Coerce row items to JSON-safe shapes; Kuzu may return
            # node-like objects, lists, dicts.
            row = [_coerce_cell(v) for v in r]
            rows.append(row)
            if len(rows) >= 1000:
                # Cap result size for inline rendering safety.
                break
    except Exception as e:
        return {"ok": False, "error": f"row iteration failed: {e}",
                "rows": rows, "columns": columns}
    return {"ok": True, "rows": rows, "columns": columns}


def _coerce_cell(v: Any) -> Any:
    """JSON-safe coercion of a single Kuzu result cell."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_coerce_cell(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _coerce_cell(val) for k, val in v.items()}
    # Kuzu node / relationship: try to extract its properties dict.
    try:
        return {str(k): _coerce_cell(val) for k, val in dict(v).items()}
    except Exception:
        return str(v)


# ---------------------------------------------------------------------------
# Pipeline: resolve cypher in a data block
# ---------------------------------------------------------------------------

def resolve_cypher_in_data(text: str, db_conn=None) -> Dict[str, Any]:
    """Detect + execute cypher segments in ``text``, returning the
    rewritten text + a structured trace.

    The result rewrites the original text so each cypher segment is
    replaced by a JSON-pretty-printed result. The trace lists each
    segment + its execution status so the frontend can render a
    diagnostic panel.

    Returns ``{ rewritten: str, trace: [{ ok, error?, segment, rows_count }] }``.
    """
    segments = detect_cypher_segments(text)
    if not segments:
        return {"rewritten": text, "trace": []}
    import json
    # Apply segments in reverse so character offsets stay valid.
    rewritten = text
    trace: List[Dict[str, Any]] = []
    for start, end, cypher in reversed(segments):
        out = execute_cypher(cypher, db_conn=db_conn)
        if out.get("ok"):
            try:
                pretty = json.dumps(
                    {"columns": out.get("columns") or [], "rows": out.get("rows") or []},
                    indent=2,
                )
            except Exception:
                pretty = str(out.get("rows") or "")
            rewritten = rewritten[:start] + pretty + rewritten[end:]
            trace.append({
                "ok": True,
                "segment": cypher[:200],
                "rows_count": len(out.get("rows") or []),
            })
        else:
            # Leave the original cypher in place; record error.
            trace.append({
                "ok": False,
                "segment": cypher[:200],
                "error": out.get("error", "?"),
            })
    trace.reverse()
    return {"rewritten": rewritten, "trace": trace}


# ---------------------------------------------------------------------------
# §8D.20 — syntax-free rendering pretty-print
# ---------------------------------------------------------------------------

# Same slug shape ``_decomposeJsonValue`` and ``_compileConceptNode``
# use in concept_graph.js. Matches alphanumerics, underscores, dashes,
# spaces, and slugs separated by dots (``module.method``).
_CONCEPT_REF_RE = re.compile(r"\{([A-Za-z][\w \-]*(?:\.[A-Za-z][\w \-]*)*)\}")


def _slugify(name: str) -> str:
    """Same slug rule as the editor's ``_conceptSlugify`` (concept_graph.js)."""
    if not name:
        return ""
    out = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
    return out.strip("_")


def resolve_concept_refs(
    text: str,
    ge=None,
    *,
    visited: Optional[Set[str]] = None,
    max_depth: int = 8,
    depth: int = 0,
) -> str:
    """Recursively substitute ``{slug}`` references with the target's
    ``data`` field (resolved transitively). Cycle-safe and depth-bounded.

    If ``ge`` is ``None`` or a referent doesn't exist, the placeholder is
    left literal (consistent with §8D.21.1 — variable auto-creation is
    a *frontend* gesture; backend resolves what's already in Database).
    """
    if not text or ge is None or depth >= max_depth:
        return text or ""
    if visited is None:
        visited = set()

    def _replace(match: "re.Match[str]") -> str:
        var = match.group(1)
        slug = _slugify(var)
        if not slug or slug in visited:
            return match.group(0)
        # First try direct concept_id lookup (when the user typed the
        # actual UUID); then fall back to name lookup (the common case
        # the editor uses — type a name, the resolver finds the concept
        # whose name slugifies to the same value).
        node = None
        try:
            node = ge.get_concept(slug)
        except Exception:
            node = None
        if node is None:
            try:
                # Fallback: scan workspace concepts for a name match.
                # Slugify both sides to make matching symmetric with
                # how `concept_graph.js` writes references.
                for candidate in (ge.list_concepts(limit=2000) or []):
                    cname = getattr(candidate, "name", "") or ""
                    if cname and _slugify(cname) == slug:
                        node = candidate
                        break
            except Exception:
                node = None
        if node is None:
            return match.group(0)
        return resolve_concept_refs(
            node.data or "",
            ge,
            visited=visited | {slug},
            max_depth=max_depth,
            depth=depth + 1,
        )

    return _CONCEPT_REF_RE.sub(_replace, text)


# ---------------------------------------------------------------------------
# §E.1 — HTML element trees + bracketed lists (the remaining strategies of
# the ONE recursive descent: "JSON, bracketed lists, indented trees, HTML
# element trees, plain text — all handled by the same routine.")
# ---------------------------------------------------------------------------

_HTML_OPEN_RE = re.compile(r"^<\s*([a-zA-Z][\w\-]*)")


def looks_like_html_tree(text: str) -> bool:
    """Gate: the text opens with a real element tag AND carries a closing
    form somewhere (``</`` or ``/>``) — a lone ``<`` in prose never
    engages the strategy."""
    if not text:
        return False
    stripped = text.strip()
    if not _HTML_OPEN_RE.match(stripped):
        return False
    return "</" in stripped or "/>" in stripped


def parse_html_tree(text: str) -> Optional[Any]:
    """§E.1 — parse an HTML element tree into plain dict/list/str structure
    (stdlib ``html.parser``; no new dependencies).

    Conversion rules (mirroring the markdown strategy's shapes so
    ``_tree_print`` + ``decompose_top_level`` walk them identically):

      * an element with only text            → that text (string);
      * an element with child elements       → ``{tag: value}`` per child,
        repeated sibling tags folding into a list under the tag;
      * interleaved text + children          → ``[text, {children}]`` (no
        authored content is dropped);
      * attributes are NOT projected — the §8D.20 clean-text tree carries
        content structure, not markup (html_raw stays on the record).

    Returns ``None`` when nothing parseable is present.
    """
    if not looks_like_html_tree(text):
        return None
    from html.parser import HTMLParser

    _VOID = {"br", "hr", "img", "input", "meta", "link", "area", "base",
             "col", "embed", "source", "track", "wbr"}

    class _Node:
        __slots__ = ("tag", "children", "text_parts")

        def __init__(self, tag: str):
            self.tag = tag
            self.children: List["_Node"] = []
            self.text_parts: List[str] = []

    class _TreeParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.root = _Node("#root")
            self.stack = [self.root]

        def handle_starttag(self, tag, attrs):
            node = _Node(tag)
            self.stack[-1].children.append(node)
            if tag.lower() not in _VOID:
                self.stack.append(node)

        def handle_endtag(self, tag):
            # Pop to the matching open tag (tolerant of mis-nesting).
            for i in range(len(self.stack) - 1, 0, -1):
                if self.stack[i].tag == tag:
                    del self.stack[i:]
                    break

        def handle_data(self, data):
            s = data.strip()
            if s:
                self.stack[-1].text_parts.append(s)

    try:
        p = _TreeParser()
        p.feed(text)
        p.close()
    except Exception:
        return None

    def _to_value(node: "_Node") -> Any:
        text_val = " ".join(node.text_parts).strip()
        if not node.children:
            return text_val
        # Children: fold repeated sibling tags into lists, preserve order.
        out: Dict[str, Any] = {}
        for child in node.children:
            v = _to_value(child)
            if child.tag in out:
                if not isinstance(out[child.tag], list):
                    out[child.tag] = [out[child.tag]]
                out[child.tag].append(v)
            else:
                out[child.tag] = v
        if text_val:
            return [text_val, out]
        return out

    root_children = p.root.children
    if not root_children:
        return None
    if len(root_children) == 1:
        # One top element: its tag keys the whole tree.
        only = root_children[0]
        return {only.tag: _to_value(only)}
    return _to_value(p.root)


def looks_like_bracketed_list(text: str) -> bool:
    """Gate: a whole-text ``[...]`` or ``(...)`` block that is NOT valid
    JSON (the JSON strategy runs first and owns strict arrays)."""
    if not text:
        return False
    s = text.strip()
    if len(s) < 2:
        return False
    pairs = {"[": "]", "(": ")"}
    if s[0] not in pairs or s[-1] != pairs[s[0]]:
        return False
    try:
        json.loads(s)
        return False  # strict JSON — the JSON strategy owns it
    except Exception:
        return True


def parse_bracketed_list(text: str) -> Optional[List[Any]]:
    """§E.1 — parse a non-JSON bracketed list (``[alpha, beta]`` /
    ``(a, b, c)``; unquoted items, nesting allowed) into a plain list.
    Top-level commas split items; nested brackets recurse; quotes guard
    embedded commas. ``None`` when the gate rejects."""
    if not looks_like_bracketed_list(text):
        return None
    s = text.strip()[1:-1]
    items: List[str] = []
    buf: List[str] = []
    depth = 0
    quote: Optional[str] = None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[({":
            depth += 1
            buf.append(ch)
        elif ch in "])}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf))
    out: List[Any] = []
    for raw in items:
        item = raw.strip()
        if not item:
            continue
        if looks_like_bracketed_list(item):
            nested = parse_bracketed_list(item)
            out.append(nested if nested is not None else item)
        else:
            # Strip one layer of symmetric quotes from string items.
            if len(item) >= 2 and item[0] == item[-1] and item[0] in "\"'":
                item = item[1:-1]
            out.append(item)
    return out if out else None


# ---------------------------------------------------------------------------
# §R.5 — markdown-gesture outline trees
# ---------------------------------------------------------------------------
#
# "when tree structures are modified with markdown editor gestures like
#  dashes, tabs, numbers, and newlines with trailing text that aren't other
#  newlines, the structure of the computation graph, the other side of the
#  dialectic representation scheme, updates accordingly." (§R.5, verbatim)
#
# One parse, shared semantics with the frontend `_parseMarkdownTopLevel`
# (concept_graph.js): dash/star bullets and `1.`/`1)` numbering open a node,
# tab/space indentation nests, a bare non-blank line ("newline with trailing
# text") is a sibling node, blank newlines are non-structural. The parse
# yields plain dict/list/str structure so `_tree_print` renders it as the
# §8D.20 syntax-free tree and the decompose path can walk it like JSON.

_MD_MARKER_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>-|\*|\d+[.)])\s+(?P<rest>\S.*)$")
_MD_KV_RE = re.compile(r"^(?P<key>[^:{}\[\]]+?):\s?(?P<val>.*)$")


def looks_like_markdown_tree(text: str) -> bool:
    """Gesture gate (§R.5): the markdown strategy engages only when at least
    one *markdown gesture* is present — a dash/star/numbered marker line, or
    tab/space indentation across a multi-line block. Pure prose (no gesture)
    falls through to the plain-text path; pure ``key: value`` rows belong to
    the indent-tree strategy."""
    if not text:
        return False
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
    if not lines:
        return False
    has_marker = any(_MD_MARKER_RE.match(ln) for ln in lines)
    if has_marker:
        return True
    if len(lines) >= 2:
        # Tab/indent gesture without bullets: an indented continuation line
        # under a flat opener nests it (the "tabs" gesture).
        return any(ln[:1] in (" ", "\t") for ln in lines[1:])
    return False


def _md_indent_width(ws: str) -> int:
    """Tab = 4 columns, space = 1 (tolerant of mixed indents)."""
    return sum(4 if c == "\t" else 1 for c in ws)


def _md_tokenize(text: str) -> List[Tuple[int, bool, str]]:
    """``[(indent_width, is_marker_line, content)]`` — blank lines dropped
    (non-structural per §R.5: only newlines *with trailing text* gesture)."""
    toks: List[Tuple[int, bool, str]] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if not raw.strip():
            continue
        m = _MD_MARKER_RE.match(raw)
        if m:
            toks.append((
                _md_indent_width(m.group("indent")), True,
                m.group("rest").strip(),
            ))
        else:
            stripped = raw.lstrip(" \t")
            ws = raw[: len(raw) - len(stripped)]
            toks.append((_md_indent_width(ws), False, stripped.rstrip()))
    return toks


def _md_parse_level(
    toks: List[Tuple[int, bool, str]], i: int, level: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """Parse the sibling run at ``level``; deeper indents recurse as children
    of the preceding sibling. Returns ``(nodes, next_index)``."""
    nodes: List[Dict[str, Any]] = []
    while i < len(toks):
        indent, _is_marker, content = toks[i]
        if indent < level:
            break
        if indent > level:
            # Ragged deeper run — children of the last sibling (or, with no
            # sibling yet, tolerate by treating the deeper indent as base).
            if nodes:
                children, i = _md_parse_level(toks, i, indent)
                nodes[-1]["children"].extend(children)
                continue
            level = indent
            continue
        node: Dict[str, Any] = {"text": content, "children": []}
        i += 1
        if i < len(toks) and toks[i][0] > level:
            node["children"], i = _md_parse_level(toks, i, toks[i][0])
        nodes.append(node)
    return nodes, i


def _md_nodes_to_value(nodes: List[Dict[str, Any]]) -> Any:
    """Plain-structure conversion: an all-``key: value`` sibling run becomes
    a dict (insertion-ordered); anything else becomes a list. A node with
    both an inline value and children carries ``[inline, children]`` so no
    authored text is dropped."""
    kv_all = bool(nodes) and all(
        (m := _MD_KV_RE.match(n["text"])) and m.group("key").strip()
        for n in nodes
    )
    if kv_all:
        out: Dict[str, Any] = {}
        for n in nodes:
            m = _MD_KV_RE.match(n["text"])
            key = m.group("key").strip()
            val = (m.group("val") or "").strip()
            if n["children"]:
                child_val = _md_nodes_to_value(n["children"])
                out[key] = [val, child_val] if val else child_val
            else:
                out[key] = val
        return out
    out_list: List[Any] = []
    for n in nodes:
        if n["children"]:
            out_list.append({n["text"]: _md_nodes_to_value(n["children"])})
        else:
            out_list.append(n["text"])
    return out_list


def parse_markdown_tree(text: str) -> Optional[Any]:
    """§R.5 — parse a markdown-gesture outline into plain dict/list/str
    structure, or ``None`` when no gesture is present (caller falls through
    to the next strategy)."""
    if not looks_like_markdown_tree(text):
        return None
    toks = _md_tokenize(text)
    if not toks:
        return None
    base = min(t[0] for t in toks)
    nodes, _ = _md_parse_level(toks, 0, base)
    if not nodes:
        return None
    return _md_nodes_to_value(nodes)


def _tree_print(value: Any, indent: int = 0) -> str:
    """§8D.20 — syntax-stripped pretty-print.

    Indentation is one tab per level. No braces, brackets, colons, or
    commas. Dict keys precede their values on the next deeper line.
    Lists drop the index (ordering carried by line position).
    Scalars become a single line.
    """
    pad = "\t" * indent
    if value is None:
        return f"{pad}null" if indent == 0 else f"{pad}∅"
    if isinstance(value, bool):
        return f"{pad}{'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{pad}{value}"
    if isinstance(value, str):
        # Multi-line strings: indent each line. Empty stays empty.
        if not value:
            return ""
        lines = value.split("\n")
        return "\n".join(f"{pad}{ln}" for ln in lines)
    if isinstance(value, dict):
        parts: List[str] = []
        for k, v in value.items():
            parts.append(f"{pad}{k}")
            child = _tree_print(v, indent + 1)
            if child:
                parts.append(child)
        return "\n".join(parts)
    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            child = _tree_print(item, indent)
            if child:
                parts.append(child)
        return "\n".join(parts)
    # Fallback: stringify and indent.
    return f"{pad}{value}"


def _entry_value_str(v: Any) -> str:
    """Render a decomposed entry's value: scalars stay verbatim, structures
    print as the §8D.20 syntax-free tree (the child card's clean-text value)."""
    if isinstance(v, str):
        return v
    return _tree_print(v, 0)


def _parse_top_level_indent_entries(text: str) -> Optional[List[Dict[str, str]]]:
    """Python port of the editor's ``_parseTopLevelIndentEntries``
    (concept_graph.js §4.2.2 IndentTree strategy): top-level ``key: value``
    rows, indented continuation lines folded into the previous entry's value
    (one indent level stripped). ``None`` when the text is not a clean
    indent tree."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    entries: List[Dict[str, str]] = []
    cur: Optional[Dict[str, str]] = None
    saw_key = False
    for raw in lines:
        if not raw.strip():
            if cur is not None:
                cur["value"] += "\n"
            continue
        if raw[:1] not in (" ", "\t"):
            m = re.match(r"^([^:{}\[\]]+?):\s?(.*)$", raw)
            if m:
                saw_key = True
                cur = {"key": m.group(1).strip(), "value": m.group(2) or ""}
                entries.append(cur)
            elif cur is not None:
                cur["value"] += ("\n" if cur["value"] else "") + raw
            else:
                return None
        else:
            if cur is None:
                return None
            cur["value"] += ("\n" if cur["value"] != "" else "") + re.sub(r"^[ \t]", "", raw)
    return entries if saw_key else None


def decompose_top_level(data: str) -> List[Dict[str, str]]:
    """§7.1 / §R.1 / §R.5 — the CANONICAL syntax-agnostic top-level
    decomposition: the entries a compile-expand turns into child cards,
    independent of authored syntax (JSON object/array, markdown-gesture
    outline, native indent tree). Strategy order mirrors the frontend
    ``_decomposeValue`` dispatcher so both dialectic sides and the REPL
    agree on the same children (§R.8 hard-verification anchor).

    Returns ``[{key, value}]`` (value = clean-text §8D.20 print for
    structured sub-trees, verbatim for scalars); ``[]`` when the text has
    no decomposable structure.
    """
    if not data:
        return []
    stripped = data.strip()
    # Strategy 1 — JSON object / array.
    if stripped and stripped[0] in "{[":
        try:
            parsed = json.loads(stripped)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return [{"key": str(k), "value": _entry_value_str(v)}
                    for k, v in parsed.items()]
        if isinstance(parsed, list):
            return [{"key": str(i), "value": _entry_value_str(v)}
                    for i, v in enumerate(parsed)]
    def _structure_entries(parsed: Any) -> List[Dict[str, str]]:
        """One shared entry-shaping rule for every structured strategy."""
        if isinstance(parsed, dict):
            return [{"key": str(k), "value": _entry_value_str(v)}
                    for k, v in parsed.items()]
        if isinstance(parsed, list):
            out: List[Dict[str, str]] = []
            for i, item in enumerate(parsed):
                if isinstance(item, dict) and len(item) == 1:
                    k, v = next(iter(item.items()))
                    out.append({"key": str(k), "value": _entry_value_str(v)})
                else:
                    out.append({"key": str(i), "value": _entry_value_str(item)})
            return out
        return []

    # Strategy 2 — §E.1 HTML element tree. A single top element decomposes
    # into its CHILDREN (the element's tag would otherwise be the lone
    # entry — the children are the components the compile splits out).
    try:
        ht = parse_html_tree(data)
    except Exception:
        ht = None
    if ht is not None:
        if isinstance(ht, dict) and len(ht) == 1:
            inner = next(iter(ht.values()))
            if isinstance(inner, (dict, list)):
                entries = _structure_entries(inner)
                if entries:
                    return entries
        entries = _structure_entries(ht)
        if entries:
            return entries
    # Strategy 3 — §E.1 non-JSON bracketed list.
    try:
        bl = parse_bracketed_list(data)
    except Exception:
        bl = None
    if bl is not None:
        entries = _structure_entries(bl)
        if entries:
            return entries
    # Strategy 4 — §R.5 markdown-gesture outline.
    try:
        md = parse_markdown_tree(data)
    except Exception:
        md = None
    if md is not None:
        entries = _structure_entries(md)
        if entries:
            return entries
    # Strategy 5 — native indent ``key: value`` tree.
    entries = _parse_top_level_indent_entries(data)
    return entries or []


def _try_parse_structured(text: str, *, _depth: int = 0) -> Optional[Any]:
    """§E.1 — THE one recursive descent's structure detector: JSON →
    HTML element tree → non-JSON bracketed list → markdown-gesture
    outline → native indent ``key: value`` tree. Returns plain
    dict/list/str structure, or ``None`` for unstructured text (the
    plain-text passthrough). Indent-tree values recurse through the same
    descent, so a ``key:`` row whose value is JSON / HTML / a list nests
    structurally. Depth-capped for safety."""
    if not text or _depth > 6:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    # 1 — strict JSON.
    if stripped[0] in "{[":
        try:
            return json.loads(stripped)
        except Exception:
            pass
    # 2 — HTML element tree.
    try:
        ht = parse_html_tree(stripped)
        if ht is not None:
            return ht
    except Exception:
        pass
    # 3 — non-JSON bracketed list.
    try:
        bl = parse_bracketed_list(stripped)
        if bl is not None:
            return bl
    except Exception:
        pass
    # 4 — markdown-gesture outline.
    try:
        md = parse_markdown_tree(stripped)
        if md is not None:
            return md
    except Exception:
        pass
    # 5 — native indent ``key: value`` tree, behind the rank-1 structure
    # gate (≥2 top-level keys, or one key with a multi-line value) so
    # prose containing a colon ("Warning: do not touch") passes through.
    entries = _parse_top_level_indent_entries(text)
    if entries and (len(entries) >= 2 or
                    (len(entries) == 1 and "\n" in entries[0]["value"])):
        out: Dict[str, Any] = {}
        for e in entries:
            v = e["value"].rstrip("\n")
            nested = _try_parse_structured(v, _depth=_depth + 1)
            out[e["key"]] = nested if nested is not None else v
        return out
    return None


def compute_rendering_tree(data: str, ge=None) -> str:
    """§8D.20 — produce the syntax-free ``rendering`` from a ``data`` block.

    Pipeline:
      1. Resolve ``{slug}`` concept references transitively (§8D.21.1).
      2. Resolve cypher patterns (§8D.2.1) — best-effort; on failure the
         original cypher remains in place.
      3. Try to parse the result as JSON; pretty-print as an indented
         tree with no syntactic punctuation.
      4. §R.5 — try the markdown-gesture outline parse (dashes, tabs,
         numbers, newline-with-trailing-text); pretty-print the same way
         so both dialectic sides agree on the structure.
      5. If neither, return the resolved text verbatim.

    Returns an empty string if ``data`` is empty.
    """
    if not data:
        return ""
    # Step 1: concept refs (only if a graph editor is available).
    resolved = resolve_concept_refs(data, ge=ge)
    # Step 2: cypher (best-effort).
    try:
        cypher_out = resolve_cypher_in_data(resolved, db_conn=getattr(ge, "_db_conn", None))
        resolved = cypher_out.get("rewritten") or resolved
    except Exception:
        pass
    # Steps 3-4: §E.1 — the ONE recursive descent over every authored
    # syntax (JSON → HTML element tree → bracketed list → §R.5 markdown
    # outline → indent tree), then the §8D.20 syntax-free pretty-print.
    try:
        parsed = _try_parse_structured(resolved)
        if parsed is not None and not isinstance(parsed, str):
            return _tree_print(parsed, 0)
    except Exception:
        pass
    # Step 5: plain text fallback.
    return resolved
