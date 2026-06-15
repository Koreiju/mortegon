"""
TF-IDF Cheeger Cut DOM Miner
=============================

Structural clustering of DOM nodes via TF-IDF vectorisation and recursive
spectral bisection (Cheeger cuts).  Designed as a drop-in replacement for
the spectral partition inside SiblingCohortMiner.

Mathematical pipeline:
  1. Extract structural terms from each content-bearing node
     (tag + agnostic attribute tokens, EXCLUDING text and URLs)
  2. Compute TF-IDF across the cohort (binary TF, smooth IDF)
  3. Build affinity matrix: cosine_sim(tfidf_i, tfidf_j)
  4. Normalised Laplacian → Fiedler vector → conductance sweep
  5. Recursive bisection with local IDF re-weighting at each level
  6. Selector extraction from top TF-IDF features per cluster

Key property: the features that DEFINE a cluster during mining are
exactly the XPath predicates that FIND the cluster on new pages.
Mining, selector generation, and cross-page matching all share the
same feature space.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Optional

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

# ---------------------------------------------------------------------------
# These are imported from the main distiller at integration time.
# For standalone testing, we define minimal interfaces.
# ---------------------------------------------------------------------------
try:
    from .shadow_html_parser import ShadowNode, ShadowDOM
    from .web_distiller_freq import (
        AttributeTokenizer,
        AgnosticAttr,
        get_absolute_xpath,
        get_subtree_signature,
        SKIP_TAGS,
        DOCUMENT_TAGS,
    )
except ImportError:
    pass  # standalone mode — caller must provide


# ═══════════════════════════════════════════════════════════════════════════
# §0  NODE TERM CACHE — Extract once, reuse everywhere
# ═══════════════════════════════════════════════════════════════════════════

class NodeTermCache:
    """
    Per-document cache for structural term extraction.

    Eliminates the 4–5× redundant extraction that occurs when the same
    nodes are tokenised in:
      1. TfIdfCheegerMiner.partition_cohort  (intra-cohort, no path)
      2. CrossCohortMerger.merge             (cross-cohort, with path)
      3. TokenizedXPathSelector._build_vocabulary  (selector tokens)
      4. CheegerChunkRefiner.refine_merge    (now eliminated)

    Stores two representations keyed by node-id:
      - term_set (set[str]):  ``{'tag:li', '@class:card', 'depth:5', ...}``
      - tok_pairs (dict[(key, tok) → 1]):  ``{('class', 'card'): 1, ...}``
    The tok_pairs format is what TokenizedXPathSelector needs, derived
    directly from the term_set without re-scanning the DOM node.

    Usage:
        cache = NodeTermCache()
        terms = cache.get_terms(node, include_path=False)
        pairs = cache.get_tok_pairs(node)  # for selector generation

    Create one per process() call and thread it through the pipeline.
    """

    def __init__(self):
        self._terms_no_path: dict[int, set[str]] = {}
        self._terms_with_path: dict[int, set[str]] = {}
        self._tok_pairs: dict[int, dict[tuple[str, str], int]] = {}

    def get_terms(self, node, include_path: bool = True) -> set[str]:
        """Get structural terms for a node, cached."""
        nid = id(node)
        store = self._terms_with_path if include_path else self._terms_no_path
        if nid not in store:
            store[nid] = StructuralTermExtractor.extract(
                node, include_path=include_path)
        return store[nid]

    def get_terms_batch(
        self, nodes: list, include_path: bool = True,
    ) -> list[set[str]]:
        """Batch extraction — cache-aware."""
        return [self.get_terms(n, include_path) for n in nodes]

    def get_tok_pairs(self, node) -> dict[tuple[str, str], int]:
        """
        Get (attr_key, token) pairs for TokenizedXPathSelector.

        Derived from cached term_set — no re-extraction from DOM.
        Terms like ``@class:card`` → ``('class', 'card')``.
        Terms like ``@data-testid`` (presence-only) → skipped (no value).
        """
        nid = id(node)
        if nid not in self._tok_pairs:
            # Derive from no-path terms (lateral attributes only)
            terms = self.get_terms(node, include_path=False)
            pairs: dict[tuple[str, str], int] = {}
            for t in terms:
                if t.startswith('@') and ':' in t:
                    # @key:token → (key, token)
                    rest = t[1:]  # strip leading @
                    key, tok = rest.split(':', 1)
                    pairs[(key, tok)] = 1
            self._tok_pairs[nid] = pairs
        return self._tok_pairs[nid]

    def stats(self) -> str:
        n1 = len(self._terms_no_path)
        n2 = len(self._terms_with_path)
        n3 = len(self._tok_pairs)
        return f"NodeTermCache: {n1} no-path, {n2} with-path, {n3} tok-pairs"


# ═══════════════════════════════════════════════════════════════════════════
# §1  STRUCTURAL TERM EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

class StructuralTermExtractor:
    """
    Extract structural-identity terms from a DOM node.

    INCLUDED (structural shape):
      Source A — tag identity                → ``tag:li``
      Source B — attribute key presence      → ``@class``
                 tokenised attribute values  → ``@class:card``, ``@class:product``
      Source C — structural context          → ``depth:5``, ``children:3``,
                                               ``leafsig:img|a|span``
      Source D — xpath-path tokens           → ``path:main``, ``pbg:main>article``
                 (vertical graph distance)     Encodes DOM topology. Shared
                                               path tokens = topological proximity.
                                               IDF naturally down-weights ubiquitous
                                               steps (div, body) and up-weights
                                               discriminative landmarks (main,
                                               article, nav, footer).
      Source E — parent structural relay     → ``parent:tag:ul``,
                                               ``parent:@class:grid``
                 (one-hop neighbourhood)       Captures the immediate structural
                                               context without full xpath.

    EXCLUDED (per-instance content):
      - visible text, aria-label, title, placeholder, alt  (text-like)
      - URL-bearing attribute values (href, src, data-src, action, ...)
      - high-entropy hash tokens (already filtered by AttributeTokenizer)
      - xpath positional indices ([2], [3]) — instance-specific, not structural

    The resulting term set is the SINGLE feature space used for:
      1. Intra-cohort Cheeger clustering (mining)
      2. XPath predicate generation (selector extraction)
      3. Cross-cohort merge (replacing signature-string matching)
      4. Cross-page matching (applying selectors to new DOMs)
    """

    # Attribute KEYS whose VALUES are human-readable text (content, not
    # structure).  Discovered empirically but kept minimal.
    _TEXT_ATTR_KEYS = frozenset({
        'title', 'alt', 'placeholder', 'aria-label', 'aria-labelledby',
        'aria-describedby', 'aria-description', 'aria-placeholder',
        'content', 'label', 'summary',
    })

    _MAX_VAL_LEN = 300  # cap tokenisation of very long values
    _MAX_PATH_DEPTH = 8  # cap ancestor walk for path tokens
    _XPATH_INDEX_RE = re.compile(r'\[\d+\]')  # strip positional indices

    @classmethod
    def extract(cls, node: ShadowNode, include_path: bool = True) -> set[str]:
        """Return the structural term set for a single node.

        Args:
            include_path: if True, include Source D (xpath-path tokens).
                Set False for intra-cohort clustering where all siblings
                share the same path prefix (the tokens would be universal
                and get zero IDF anyway).  Set True for cross-cohort
                merge and cross-page matching where path tokens encode
                topological distance.
        """
        terms: set[str] = set()

        # ── Source A: tag identity ────────────────────────────────
        tag = node.tag.lower()
        terms.add(f"tag:{tag}")

        # ── Source B: agnostic attribute predicates ───────────────
        for key, val in node.get_all_attrs().items():
            key_lower = key.lower()

            # Skip text-like attribute values
            if key_lower in cls._TEXT_ATTR_KEYS:
                continue

            # Presence token: XPath [@key]
            terms.add(f"@{key_lower}")

            if not val or not isinstance(val, str):
                continue

            val_str = val[:cls._MAX_VAL_LEN]

            # Skip URL-bearing values entirely
            if AgnosticAttr.is_url(val_str):
                continue

            # Tokenise the value (space, snake_case, camelCase, kebab-case)
            for tok in AttributeTokenizer.tokenize(val_str):
                terms.add(f"@{key_lower}:{tok}")

        # ── Source C: structural context ──────────────────────────
        children = node.get_children(include_shadow=True)
        n_children = len(children)
        if n_children == 0:
            terms.add("children:0")
        elif n_children <= 3:
            terms.add(f"children:{n_children}")
        elif n_children <= 8:
            terms.add("children:4-8")
        else:
            terms.add("children:9+")

        # Depth-1 leaf-tag signature (ordered child tag sequence)
        if children:
            child_tags = [c.tag.lower() for c in children
                          if not c.tag.startswith('#')]
            if child_tags:
                sig = '|'.join(child_tags[:12])  # cap to avoid explosion
                terms.add(f"leafsig:{sig}")

        # ── Source D: xpath-path tokens (vertical distance) ───────
        if include_path:
            # Walk ancestors, collect tag-only path steps (strip indices)
            path_steps: list[str] = []
            anc = node.parent
            depth = 0
            while anc and depth < cls._MAX_PATH_DEPTH:
                anc_tag = anc.tag.lower()
                if not anc_tag.startswith('#'):
                    path_steps.append(anc_tag)
                anc = anc.parent
                depth += 1

            # Reverse so path_steps[0] is root-ward, [-1] is parent
            path_steps.reverse()

            # Depth token (always useful)
            terms.add(f"depth:{len(path_steps)}")

            # Unigrams: each ancestor tag as a path token
            # IDF naturally down-weights 'div'/'body' and up-weights
            # 'main'/'article'/'nav'/'footer'
            for step in path_steps:
                terms.add(f"path:{step}")

            # Bigrams: adjacent tag pairs encode local topology
            # 'pbg:main>article' distinguishes content-area cards from
            # 'pbg:nav>ul' navigation items even when both have 'li' tag
            for i in range(len(path_steps) - 1):
                terms.add(f"pbg:{path_steps[i]}>{path_steps[i+1]}")

            # Terminal bigram: immediate parent>self relationship
            if path_steps:
                terms.add(f"pbg:{path_steps[-1]}>{tag}")
        else:
            # Still compute depth for structural context
            depth = 0
            anc = node.parent
            while anc:
                depth += 1
                anc = anc.parent
            terms.add(f"depth:{depth}")

        # ── Source E: parent structural relay ─────────────────────
        # One-hop neighbourhood: parent's tag + top attribute tokens
        # This captures immediate structural context without full path
        parent = node.parent
        if parent and not parent.tag.startswith('#'):
            terms.add(f"parent:tag:{parent.tag.lower()}")
            for key, val in parent.get_all_attrs().items():
                key_lower = key.lower()
                if key_lower in cls._TEXT_ATTR_KEYS:
                    continue
                if not val or not isinstance(val, str):
                    continue
                if AgnosticAttr.is_url(val[:200]):
                    continue
                for tok in AttributeTokenizer.tokenize(val[:200]):
                    terms.add(f"parent:@{key_lower}:{tok}")

        return terms


# ═══════════════════════════════════════════════════════════════════════════
# §2  TF-IDF VECTORISER
# ═══════════════════════════════════════════════════════════════════════════

class DomTfIdf:
    """
    TF-IDF vectorisation of DOM nodes using structural terms.

    Binary TF (appropriate for categorical DOM attributes) combined with
    smooth IDF: ``idf(t) = log(1 + N / df(t))`` (add-one smoothing to
    avoid log(0) for terms appearing in all documents).

    The resulting vectors are L2-normalised for cosine similarity via
    dot product.
    """

    def __init__(self):
        self.vocab: dict[str, int] = {}       # term → column index
        self.idf: np.ndarray = np.array([])   # IDF weights per term
        self.vectors: sparse.csr_matrix = sparse.csr_matrix((0, 0))
        self._term_sets: list[set[str]] = []  # raw terms per node

    def fit_transform(self, term_sets: list[set[str]]) -> sparse.csr_matrix:
        """
        Compute TF-IDF vectors for a list of term sets.

        Args:
            term_sets: one set of structural terms per DOM node

        Returns:
            Sparse CSR matrix of shape (N, V) — L2-normalised TF-IDF vectors
        """
        self._term_sets = term_sets
        N = len(term_sets)
        if N == 0:
            return sparse.csr_matrix((0, 0))

        # ── Build vocabulary ──────────────────────────────────────
        df: dict[str, int] = defaultdict(int)
        for ts in term_sets:
            for t in ts:
                df[t] += 1

        # Vocabulary: all terms with 1 < df < N (exclude unique + universal)
        # Unique terms (df=1) have no discriminative power within a cohort.
        # Universal terms (df=N) have zero IDF — mathematically useless.
        self.vocab = {}
        idx = 0
        for t, freq in sorted(df.items()):
            if 1 < freq < N:
                self.vocab[t] = idx
                idx += 1

        V = len(self.vocab)
        if V == 0:
            # All terms are either unique or universal — fall back to
            # including universal terms (they still carry tag identity)
            for t, freq in sorted(df.items()):
                if freq > 1:
                    self.vocab[t] = len(self.vocab)
            V = len(self.vocab)
            if V == 0:
                return sparse.csr_matrix((N, 0))

        # ── Compute IDF ──────────────────────────────────────────
        self.idf = np.zeros(V)
        for t, col in self.vocab.items():
            self.idf[col] = math.log(1.0 + N / df[t])

        # ── Build sparse TF-IDF matrix ───────────────────────────
        rows, cols, data = [], [], []
        for i, ts in enumerate(term_sets):
            for t in ts:
                if t in self.vocab:
                    col = self.vocab[t]
                    rows.append(i)
                    cols.append(col)
                    data.append(self.idf[col])  # binary TF × IDF = IDF

        mat = sparse.csr_matrix(
            (np.array(data, dtype=np.float64),
             (np.array(rows), np.array(cols))),
            shape=(N, V),
        )

        # ── L2 normalise rows ────────────────────────────────────
        norms = sparse.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1.0  # avoid division by zero
        mat = sparse.diags(1.0 / norms) @ mat

        self.vectors = mat
        return mat

    def top_features(
        self, indices: list[int], k: int = 5,
        min_coverage: float = 0.7,
    ) -> list[tuple[str, float]]:
        """
        Extract top-k TF-IDF features for a cluster of nodes.

        Filters by coverage (fraction of cluster nodes containing the
        feature) and ranks by mean TF-IDF weight within the cluster.

        Args:
            indices: row indices of the cluster nodes
            k: max features to return
            min_coverage: minimum fraction of cluster nodes with the feature

        Returns:
            List of (term_string, mean_tfidf_weight) pairs
        """
        if not indices or self.vectors.shape[1] == 0:
            return []

        # Sub-matrix for this cluster
        sub = self.vectors[indices, :]
        n = len(indices)

        # Coverage: fraction of cluster nodes with non-zero value per term
        binary = (sub > 0).astype(float)
        coverage = np.asarray(binary.sum(axis=0)).flatten() / n

        # Mean TF-IDF weight per term
        mean_weights = np.asarray(sub.mean(axis=0)).flatten()

        # Reverse vocab lookup
        idx_to_term = {v: k for k, v in self.vocab.items()}

        # Filter by coverage, rank by weight
        candidates = []
        for col in range(sub.shape[1]):
            if coverage[col] >= min_coverage and mean_weights[col] > 0:
                term = idx_to_term.get(col, '')
                if term:
                    candidates.append((term, float(mean_weights[col])))

        candidates.sort(key=lambda x: -x[1])
        return candidates[:k]


# ═══════════════════════════════════════════════════════════════════════════
# §3  CHEEGER CUT (SPECTRAL BISECTION)
# ═══════════════════════════════════════════════════════════════════════════

class CheegerCut:
    """
    Optimal graph bisection via the Fiedler vector of the normalised
    Laplacian, with level-set sweep for minimum conductance.

    The Cheeger constant h* of the returned cut satisfies:
        h* ≤ √(2 λ₂)     (Cheeger's inequality)

    This is mathematically identical to the current _spectral_bisect,
    but operates on a DIRECT node-to-node affinity matrix (cosine
    similarity of TF-IDF vectors) rather than a bipartite projection.
    """

    @staticmethod
    def bisect(
        W: np.ndarray,
    ) -> tuple[list[int], list[int], float, float]:
        """
        Perform a Cheeger cut on the affinity matrix W.

        Args:
            W: symmetric affinity matrix (N × N), non-negative

        Returns:
            (left_indices, right_indices, cheeger_constant, lambda2)
            Returns ([], [], 1.0, 2.0) if bisection fails.
        """
        n = W.shape[0]
        if n < 4:
            return [], [], 1.0, 2.0

        degrees = W.sum(axis=1)
        if np.any(degrees <= 1e-10):
            return [], [], 1.0, 2.0

        # Normalised Laplacian: L_norm = I - D^{-1/2} W D^{-1/2}
        D_inv_sqrt = np.diag(1.0 / np.sqrt(degrees))
        L_norm = np.eye(n) - D_inv_sqrt @ W @ D_inv_sqrt

        # Ensure symmetry (numerical stability)
        L_norm = (L_norm + L_norm.T) / 2.0

        try:
            # For small matrices, use dense eigendecomposition
            if n <= 64:
                vals, vecs = np.linalg.eigh(L_norm)
            else:
                L_sparse = sparse.csr_matrix(L_norm)
                k = min(n - 1, 3)
                vals, vecs = eigsh(L_sparse, k=k, which='SM', tol=1e-4)

            # Sort by eigenvalue (ascending)
            order = np.argsort(vals)
            vals = vals[order]
            vecs = vecs[:, order]

            if len(vals) < 2:
                return [], [], 1.0, 2.0

            lambda2 = float(vals[1])
            fiedler = vecs[:, 1]
        except Exception:
            return [], [], 1.0, 2.0

        # ── Level-set sweep for minimum conductance ──────────────
        sorted_idx = np.argsort(fiedler)
        total_vol = float(degrees.sum())

        in_left = set()
        vol_left = 0.0
        cut_val = 0.0
        best_cond = float('inf')
        best_split = -1

        for split_i in range(n - 1):
            u = int(sorted_idx[split_i])
            in_left.add(u)
            vol_left += degrees[u]

            # Update cut value
            for v in range(n):
                if W[u, v] > 0:
                    if v in in_left:
                        cut_val -= W[u, v]
                    else:
                        cut_val += W[u, v]

            vol_right = total_vol - vol_left
            denom = min(vol_left, vol_right)
            if denom <= 1e-10:
                continue

            cond = cut_val / denom
            if cond < best_cond:
                best_cond = cond
                best_split = split_i + 1

        if best_split <= 0 or best_split >= n:
            return [], [], 1.0, lambda2

        left = [int(sorted_idx[i]) for i in range(best_split)]
        right = [int(sorted_idx[i]) for i in range(best_split, n)]

        return left, right, float(best_cond), lambda2


# ═══════════════════════════════════════════════════════════════════════════
# §4  RECURSIVE TF-IDF CHEEGER MINER
# ═══════════════════════════════════════════════════════════════════════════

class TfIdfCheegerMiner:
    """
    Recursive DOM clustering via TF-IDF vectorisation and Cheeger cuts.

    Algorithm:
      1. Extract structural terms for each sibling
      2. Compute TF-IDF within the cohort
      3. Build cosine-similarity affinity matrix
      4. Cheeger cut → bisect if h* < threshold
      5. For each half: recompute local TF-IDF (recursive IDF re-weighting)
      6. Repeat until h* > threshold or cluster too small

    Each final cluster's top TF-IDF features directly yield the
    portable XPath selector predicates.
    """

    # ── Tuning parameters ─────────────────────────────────────────
    CHEEGER_THRESHOLD = 0.50   # stop bisecting when h* exceeds this
    LAMBDA2_CEILING   = 0.80   # stop when algebraic connectivity too high
    MIN_CLUSTER_SIZE  = 2      # minimum nodes for a valid chunk
    MAX_DEPTH         = 12     # recursion safety limit
    MIN_COSINE_SIM    = 0.05   # sparsify affinity below this

    def __init__(self, verbose: bool = False,
                 cache: NodeTermCache | None = None):
        self.verbose = verbose
        self._log = print if verbose else lambda *a, **k: None
        self._cache = cache or NodeTermCache()

    def partition_cohort(
        self, siblings: list[ShadowNode],
    ) -> list[list[ShadowNode]]:
        """
        Partition a sibling cohort into structurally homogeneous clusters.

        Uses include_path=False because all siblings share the same xpath
        prefix — path tokens would be universal (IDF ≈ 0) and waste
        feature budget.  Lateral attribute tokens do all the work here.

        Returns:
            List of clusters, each a list of ShadowNode.
        """
        m = len(siblings)
        if m < self.MIN_CLUSTER_SIZE:
            return [siblings] if siblings else []

        # ── Step 1: extract structural terms (cached, no path) ────
        term_sets = self._cache.get_terms_batch(siblings, include_path=False)

        # ── Step 2-5: recursive TF-IDF Cheeger bisection ─────────
        indices = list(range(m))
        final_clusters: list[list[int]] = []
        self._recursive_bisect(term_sets, indices, 0, final_clusters)

        # ── Map indices back to nodes ─────────────────────────────
        return [[siblings[i] for i in cluster] for cluster in final_clusters]

    def partition_cohort_with_selectors(
        self, siblings: list[ShadowNode],
    ) -> list[tuple[list[ShadowNode], str]]:
        """
        Partition AND generate portable XPath selectors for each cluster.

        Returns:
            List of (cluster_nodes, xpath_selector) tuples.
        """
        m = len(siblings)
        if m < self.MIN_CLUSTER_SIZE:
            return [(siblings, '')] if siblings else []

        term_sets = self._cache.get_terms_batch(siblings, include_path=True)
        indices = list(range(m))
        final_clusters: list[list[int]] = []
        self._recursive_bisect(term_sets, indices, 0, final_clusters)

        # ── Generate selectors from top TF-IDF features ──────────
        results: list[tuple[list[ShadowNode], str]] = []
        for cluster in final_clusters:
            nodes = [siblings[i] for i in cluster]
            cluster_terms = [term_sets[i] for i in cluster]

            # Compute local TF-IDF for selector extraction
            tfidf = DomTfIdf()
            tfidf.fit_transform(cluster_terms)
            top_feats = tfidf.top_features(
                list(range(len(cluster))), k=5, min_coverage=0.7,
            )
            selector = self._features_to_xpath(nodes, top_feats)
            results.append((nodes, selector))

        return results

    def _recursive_bisect(
        self,
        term_sets: list[set[str]],
        indices: list[int],
        depth: int,
        out_clusters: list[list[int]],
    ) -> None:
        """
        Recursive TF-IDF Cheeger bisection.

        At each level:
          1. Compute LOCAL TF-IDF (IDF is relative to this sub-cohort)
          2. Build cosine-similarity affinity matrix
          3. Cheeger cut → evaluate quality
          4. If good split: recurse on each half
          5. If bad split: emit as final cluster
        """
        n = len(indices)

        if n < 4 or depth > self.MAX_DEPTH:
            if n >= self.MIN_CLUSTER_SIZE:
                out_clusters.append(indices)
            return

        # ── Local TF-IDF ─────────────────────────────────────────
        local_terms = [term_sets[i] for i in indices]
        tfidf = DomTfIdf()
        vectors = tfidf.fit_transform(local_terms)

        if vectors.shape[1] == 0:
            # No discriminative features — emit as single cluster
            if n >= self.MIN_CLUSTER_SIZE:
                out_clusters.append(indices)
            return

        # ── Cosine similarity affinity matrix ─────────────────────
        # Since vectors are L2-normalised, cosine_sim = dot product
        W = (vectors @ vectors.T).toarray()

        # Zero out self-loops and sub-threshold entries
        np.fill_diagonal(W, 0.0)
        W[W < self.MIN_COSINE_SIM] = 0.0

        # Check if graph is trivially disconnected
        connected = np.any(W > 0, axis=1)
        if not np.all(connected):
            # Some nodes have zero affinity — split into connected/isolated
            conn_idx = [indices[i] for i in range(n) if connected[i]]
            isol_idx = [indices[i] for i in range(n) if not connected[i]]

            if len(conn_idx) >= self.MIN_CLUSTER_SIZE:
                self._recursive_bisect(
                    term_sets, conn_idx, depth + 1, out_clusters,
                )
            if len(isol_idx) >= self.MIN_CLUSTER_SIZE:
                out_clusters.append(isol_idx)
            return

        # ── Cheeger cut ──────────────────────────────────────────
        left_local, right_local, h_star, lambda2 = CheegerCut.bisect(W)

        # ── Accept/reject decision ───────────────────────────────
        left_count = len(left_local)
        right_count = len(right_local)

        accept = (
            h_star < self.CHEEGER_THRESHOLD
            and lambda2 < self.LAMBDA2_CEILING
            and left_count >= self.MIN_CLUSTER_SIZE
            and right_count >= self.MIN_CLUSTER_SIZE
        )

        if accept:
            left_idx = [indices[i] for i in left_local]
            right_idx = [indices[i] for i in right_local]
            self._recursive_bisect(
                term_sets, left_idx, depth + 1, out_clusters,
            )
            self._recursive_bisect(
                term_sets, right_idx, depth + 1, out_clusters,
            )
        else:
            # Cluster is cohesive — emit as final cluster
            if n >= self.MIN_CLUSTER_SIZE:
                out_clusters.append(indices)

    @staticmethod
    def _features_to_xpath(
        nodes: list[ShadowNode],
        features: list[tuple[str, float]],
    ) -> str:
        """
        Convert top TF-IDF features to an XPath selector.

        Feature format: ``@{key}:{token}`` → ``[contains(@key,'token')]``
        Feature format: ``tag:{name}``     → tag name in selector
        """
        from collections import Counter
        tag_counts = Counter(n.tag.lower() for n in nodes)
        common_tag = tag_counts.most_common(1)[0][0]

        predicates = []
        for feat, _weight in features:
            if feat.startswith('tag:'):
                continue  # tag already captured
            if feat.startswith('@') and ':' in feat:
                # @key:token → [contains(@key,'token')]
                parts = feat.split(':', 1)
                attr_key = parts[0][1:]  # strip leading @
                token = parts[1]
                predicates.append(f"[contains(@{attr_key},'{token}')]")
            elif feat.startswith('@'):
                # @key → [@key]
                attr_key = feat[1:]
                predicates.append(f"[@{attr_key}]")

        return f".//{common_tag}{''.join(predicates[:5])}"


# ═══════════════════════════════════════════════════════════════════════════
# §5  CROSS-COHORT TF-IDF MERGE
# ═══════════════════════════════════════════════════════════════════════════

class CrossCohortMerger:
    """
    Replace signature-string merge with TF-IDF cosine-similarity merge.

    The dual-space tokenization makes this mathematically clean:
    - **Intra-cohort** clustering uses include_path=False (Source A+B+C+E)
      because siblings share xpath prefix (it would be universal, IDF=0)
    - **Cross-cohort** merge uses include_path=True (Source A+B+C+D+E)
      where the xpath-path tokens (Source D) encode topological distance

    Two clusters from different cohorts merge when their mean TF-IDF
    vectors (with path tokens) have cosine similarity > threshold.

    This is mathematically superior to signature-string matching because:
    1. Signatures are binary (match or don't) — cosine is continuous
    2. Signatures capture subtree shape only — TF-IDF captures shape +
       topology + attribute identity simultaneously
    3. Signatures require heuristic adaptive depth — TF-IDF naturally
       weights features by discriminative power (IDF)
    """

    MERGE_COS_THRESHOLD = 0.55  # legacy — unused by hash merge
    COVERAGE_THRESHOLD = 0.70   # min fraction of nodes with a feature
    MIN_CLUSTER_FREQ = 2        # minimum merged cluster size

    def __init__(self, verbose: bool = False,
                 cache: NodeTermCache | None = None):
        self.verbose = verbose
        self._log = print if verbose else lambda *a, **k: None
        self._cache = cache or NodeTermCache()

    def merge(
        self,
        raw_groups: list[tuple[list[ShadowNode], ShadowNode]],
    ) -> list[tuple[list[ShadowNode], str, np.ndarray]]:
        """
        O(N) feature-hash cross-cohort merge.

        Instead of O(N²) pairwise centroid cosine similarity, computes a
        compact structural fingerprint per group and merges by dictionary
        lookup.

        The fingerprint is the sorted set of structural terms that appear
        in ≥ COVERAGE_THRESHOLD of the group's nodes, EXCLUDING per-instance
        terms (depth, child count) and rare terms.  This captures the
        *structural identity* of the group — exactly the set of features
        that would become XPath predicates.

        Two groups merge iff their fingerprints are identical.  This is
        stricter than the previous 0.55 cosine threshold (which caused
        massive over-merging: 1302 span groups → single blob).

        Time complexity: O(N × T) where N = total nodes, T = terms per node.
        Space: O(G) merge groups via dictionary, G = unique fingerprints.

        Args:
            raw_groups: list of (cluster_nodes, parent_node) from per-cohort
                        partitioning

        Returns:
            list of (merged_nodes, selector_string, zero_centroid) triples
            (centroid is a placeholder — not used downstream)
        """
        if not raw_groups:
            return []

        # ── Step 1: Compute structural fingerprint per group ─────────
        # Uses cached terms — no redundant DOM access.
        merge_buckets: dict[str, list[int]] = defaultdict(list)

        for gi, (members, parent) in enumerate(raw_groups):
            fp = self._structural_fingerprint(members)
            merge_buckets[fp].append(gi)

        # ── Step 2: Collect merged groups ────────────────────────────
        results: list[tuple[list[ShadowNode], str, np.ndarray]] = []
        seen_node_ids: set[int] = set()

        for fp, group_indices in merge_buckets.items():
            # Dedup nodes across merged groups
            merged_nodes: list[ShadowNode] = []
            for gi in group_indices:
                members, _parent = raw_groups[gi]
                for node in members:
                    if id(node) not in seen_node_ids:
                        seen_node_ids.add(id(node))
                        merged_nodes.append(node)

            if len(merged_nodes) < self.MIN_CLUSTER_FREQ:
                continue

            # Generate selector from fingerprint features
            selector = self._fingerprint_to_xpath(merged_nodes, fp)

            if len(group_indices) > 1:
                self._log(
                    f"  [hash-merge] Merged {len(group_indices)} clusters → "
                    f"{len(merged_nodes)} nodes, selector={selector}"
                )

            # Centroid placeholder (not used downstream)
            results.append((merged_nodes, selector, np.zeros(1)))

        return results

    def _structural_fingerprint(
        self, members: list[ShadowNode],
    ) -> str:
        """
        Compute the structural identity fingerprint for a group.

        The fingerprint is the sorted canonical set of structural terms
        that appear in ≥ 70% of the group's nodes, excluding:
        - depth:* (varies across cohorts even for same template)
        - children:* (varies with optional children)
        - path:* bigrams (too location-specific for cross-cohort merge)

        Includes:
        - tag:* (structural tag identity)
        - @key:token (attribute predicates — the XPath features)
        - leafsig:* (child-tag signature — structural shape)
        - parent:tag:* (immediate context — prevents nav/content conflation)
        - parent:@key:token (parent attribute context)

        This fingerprint IS the structural template.  Two groups with
        identical fingerprints are the same DOM component pattern.
        """
        n = len(members)
        if n == 0:
            return ''

        # Count term frequency across all nodes (using cached terms)
        term_freq: dict[str, int] = defaultdict(int)
        for node in members:
            # Use include_path=True to get parent context (Source E)
            # but we'll filter out the path-specific terms below
            terms = self._cache.get_terms(node, include_path=True)
            for t in terms:
                term_freq[t] += 1

        # Coverage threshold: ≥70% of instances must have the term
        threshold = max(1, int(n * self.COVERAGE_THRESHOLD))

        # Filter: keep high-coverage terms, exclude location-specific
        core_terms: list[str] = []
        for t, freq in term_freq.items():
            if freq < threshold:
                continue
            # Exclude per-instance/location terms
            if t.startswith('depth:'):
                continue
            if t.startswith('children:'):
                continue
            # Exclude path bigrams (too specific to DOM location)
            if t.startswith('pbg:'):
                continue
            # Exclude path unigrams (would prevent cross-cohort merge
            # of structurally identical components at different depths)
            if t.startswith('path:'):
                continue
            core_terms.append(t)

        core_terms.sort()
        return '|'.join(core_terms)

    @staticmethod
    def _fingerprint_to_xpath(
        nodes: list[ShadowNode], fingerprint: str,
    ) -> str:
        """Convert a structural fingerprint to an XPath selector."""
        if not fingerprint:
            return ''

        from collections import Counter
        tag_counts = Counter(n.tag.lower() for n in nodes)
        common_tag = tag_counts.most_common(1)[0][0]

        predicates = []
        for feat in fingerprint.split('|'):
            if feat.startswith('tag:'):
                continue  # tag already captured
            if feat.startswith('@') and ':' in feat:
                # @key:token → [contains(@key,'token')]
                parts = feat.split(':', 1)
                attr_key = parts[0][1:]  # strip @
                token = parts[1]
                predicates.append(f"[contains(@{attr_key},'{token}')]")
            elif feat.startswith('@'):
                attr_key = feat[1:]
                predicates.append(f"[@{attr_key}]")

        return f".//{common_tag}{''.join(predicates[:5])}"


# ═══════════════════════════════════════════════════════════════════════════
# §6  INTEGRATION BRIDGE
# ═══════════════════════════════════════════════════════════════════════════

def tfidf_cheeger_partition(
    siblings: list[ShadowNode],
    verbose: bool = False,
    cache: NodeTermCache | None = None,
) -> list[list[ShadowNode]]:
    """
    Drop-in replacement for the spectral partition in SiblingCohortMiner.

    Usage in _partition_cohort:
        # OLD: return self._spectral_partition_purified(siblings, sig_map)
        # NEW: return tfidf_cheeger_partition(siblings, cache=self._term_cache)
    """
    miner = TfIdfCheegerMiner(verbose=verbose, cache=cache)
    return miner.partition_cohort(siblings)


# ═══════════════════════════════════════════════════════════════════════════
# §6  DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

def diagnose_cohort(siblings: list[ShadowNode]) -> dict:
    """
    Full diagnostic report for a sibling cohort.

    Returns:
        Dictionary with term analysis, TF-IDF weights, cluster
        assignments, Cheeger constants, and generated selectors.
    """
    cache = NodeTermCache()
    miner = TfIdfCheegerMiner(verbose=True, cache=cache)
    term_sets = cache.get_terms_batch(siblings, include_path=True)

    # Global TF-IDF
    tfidf = DomTfIdf()
    vectors = tfidf.fit_transform(term_sets)

    # Cluster
    results = miner.partition_cohort_with_selectors(siblings)

    # Diagnostics
    diag = {
        'n_siblings': len(siblings),
        'n_features': vectors.shape[1] if vectors.shape[1] else 0,
        'vocabulary': dict(tfidf.vocab),
        'idf_weights': {
            t: float(tfidf.idf[idx])
            for t, idx in tfidf.vocab.items()
        },
        'clusters': [],
    }

    for nodes, selector in results:
        cluster_diag = {
            'size': len(nodes),
            'tags': [n.tag.lower() for n in nodes],
            'selector': selector,
            'top_features': [],
        }

        # Get top features for this specific cluster
        cluster_terms = cache.get_terms_batch(nodes, include_path=True)
        local_tfidf = DomTfIdf()
        local_tfidf.fit_transform(cluster_terms)
        feats = local_tfidf.top_features(
            list(range(len(nodes))), k=8, min_coverage=0.5,
        )
        cluster_diag['top_features'] = [
            {'term': t, 'weight': round(w, 3)} for t, w in feats
        ]

        diag['clusters'].append(cluster_diag)

    return diag
