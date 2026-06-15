"""
demo_scanner.py -- End-to-end scanner demo, now instance-level + reasoned.

Pipeline stages exercised in one shot:

1. Scan a URL with Selenium -> ShadowDOM.
2. Content-tag the DOM, collapse into a Patricia trie of *only* content-
   bearing xpaths (the "distilled" tree).
3. Partition the distilled trie into chunks; render every populated
   chunk instance to HTML + markdown-lite text.
4. Instrumentation header — raw DOM node count vs. distilled tree node
   count vs. chunks vs. non-empty instances vs. unique content hashes.
   This is how we *see* whether dedup is actually biting.
5. For every non-empty chunk instance, build a feature vector from five
   graph-analytic algorithms over the **content-distilled** augmented
   graph (NOT the raw DOM):

       a. Tree metrics    -- Strahler, Sackin-z, Colless
       b. Weisfeiler-Leman structural coloring (k=3)
       c. Heat Kernel Signature at three diffusion times
       d. Sarkar Poincaré ball embedding (tau=0.4)
       e. Graphlet Degree Vector (orbits 0-7)

   Each hyperparameter is justified in a console banner so the reasoning
   travels with the experiment.
6. Standardize, PCA-denoise, then cluster instances with cuML DBSCAN on
   cupy (falls back to sklearn). eps is selected empirically from the
   k-distance knee, not hard-coded.
7. Save four diagnostic plots:
       - umap_chunks.png           (semantic nomic embedding)
       - dbscan_clusters.png       (3D PCA coloured by cluster)
       - kdist_knee.png            (k-distance elbow that picked eps)
       - feature_variance.png      (variance contribution per feature)
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import scipy.linalg as la
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler, StandardScaler

import backend.database as database
from backend.analytics.algorithms.centrality import CentralityAlgorithms, SpectralAlgorithms
from backend.analytics.algorithms.cohesive import CohesiveAlgorithms
from backend.analytics.algorithms.curvature import CurvatureSignatures
from backend.analytics.algorithms.graph_invariants import (
    AlgebraicInvariants,
    AncestryProfile,
    LocalTotalVariation,
    TopologicalFeatures,
    WLMultiplicitySpectrum,
)
from backend.analytics.algorithms.graphlets import GraphletDegreeVector
from backend.analytics.algorithms.hyperbolic_embeddings import HyperbolicEmbeddings
from backend.analytics.algorithms.path_decomposition import PathDecompositionAlgorithms
from backend.analytics.algorithms.spectral import SpectralSignatures
from backend.analytics.algorithms.structural import (
    FrequencyAlgorithms,
    InformationTheoreticAlgorithms,
    StructuralAlgorithms,
)
from backend.analytics.algorithms.topology import TopologicalSignatures
from backend.analytics.algorithms.tree_kernels import TreeKernels
from backend.analytics.algorithms.tree_metrics import (
    DAGCompressionAlgorithms,
    StrahlerAlgorithm,
    TreeBalanceAlgorithms,
)
from backend.analytics.algorithms.wavelets import SpectralGraphWavelets
from backend.dom.pipeline import run_pipeline_live
from backend.mapper.chunk_builder import HARD_CHAR_LIMIT, HARD_TOKEN_LIMIT
from backend.services.chunk_instance_embedder import ChunkInstanceEmbedder
from backend.services.chunk_instance_persistence import load_all_instances
from backend.services.xpath_utils import generalize_xpath

try:
    import cupy as cp  # noqa: F401
    from cuml.cluster import DBSCAN as cuDBSCAN
    USE_CUML = True
except Exception:
    USE_CUML = False

from sklearn.cluster import DBSCAN as skDBSCAN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_scanner")


HTML_PREVIEW_LIMIT = 256  # user-requested truncation ceiling


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "..."


def _banner(title: str, char: str = "=") -> None:
    bar = char * 72
    print(f"\n{bar}\n{title}\n{bar}")


# ---------------------------------------------------------------------------
# Instrumentation: is dedup really biting?
# ---------------------------------------------------------------------------


def print_pipeline_instrumentation(result) -> None:
    """Surface the counts that decide whether dedup is working.

    The suspicion was that "non-empty instances / chunks" were exploding.
    We print every number that feeds those totals so the provenance is
    visible: raw DOM nodes (full tree), distilled content xpaths (only
    tagged), distilled tree nodes (after Patricia collapse), then chunks
    and instances. A big jump from distilled-xpaths to instances means
    the Patricia collapse is leaking; a big jump from instances to
    ``unique_html_hash`` means dedup isn't biting at the render layer.
    """
    raw_dom_nodes = sum(1 for _ in result.dom.iter_all())
    distilled_content_xpaths = len(result.tagged.all_content_xpaths())
    tree_nodes = _count_tree_nodes(result.content_tree)
    pattern_count = len(result.trie.patterns)

    instances = result.instances or []
    unique_html = {
        hashlib.sha1((i.html_raw or "").encode()).hexdigest() for i in instances
    }
    unique_text = {
        hashlib.sha1((i.rendered_text or "").encode()).hexdigest()
        for i in instances
    }
    unique_patterns = {i.pattern for i in instances}

    _banner("Pipeline instrumentation (is dedup biting?)")
    print(f"  Raw DOM nodes (full shadow tree):     {raw_dom_nodes:>6}")
    print(f"  Distilled content xpaths (tagged):    {distilled_content_xpaths:>6}")
    print(f"  Distilled tree nodes (after Patricia):{tree_nodes:>6}")
    print(f"  Unique content patterns (generalized):{pattern_count:>6}")
    print(f"  Chunks produced:                      {len(result.chunks):>6}")
    print(f"  Non-empty ChunkInstances rendered:    {len(instances):>6}")
    print(f"  Unique instance html hashes:          {len(unique_html):>6}")
    print(f"  Unique instance text hashes:          {len(unique_text):>6}")
    print(f"  Unique patterns covering instances:   {len(unique_patterns):>6}")

    # Red flags
    distill_ratio = distilled_content_xpaths / max(raw_dom_nodes, 1)
    print(f"\n  distilled / raw ratio:    {distill_ratio:.3f}"
          f"   (lower = more aggressive content-distillation)")
    if instances:
        dup_ratio = 1.0 - (len(unique_html) / len(instances))
        print(f"  instance dedup ratio:     {dup_ratio:.3f}"
              f"   (higher = more duplicate html_raw — dedup NOT biting)")
        if dup_ratio > 0.05:
            print("  !! WARNING: >5% of rendered instances share the same HTML.")
            print("     Dedup should collapse these; inspect render path.")

    # Per-chunk member vs rendered count — catches leaky generalization.
    print("\n  Per-chunk: |members| vs |rendered non-empty instances|")
    header = f"    {'rendered':>10} {'members':>9}  pattern"
    print(header)
    for ch in result.chunks[:10]:
        n_rendered = sum(1 for i in instances if i.chunk_id == ch.chunk_id)
        print(f"    {n_rendered:>10} {len(ch.member_xpaths):>9}  {ch.pattern}")
    if len(result.chunks) > 10:
        print(f"    ...{len(result.chunks) - 10} more chunks")


def _count_tree_nodes(tree: Dict[str, Any]) -> int:
    n = 0
    for key, sub in tree.items():
        if key.startswith("_") or not isinstance(sub, dict):
            continue
        n += 1 + _count_tree_nodes(sub)
    return n


# ---------------------------------------------------------------------------
# First-instance-only per-chunk preview
# ---------------------------------------------------------------------------


def print_first_instance_per_chunk(result) -> None:
    """One preview row per chunk — the first surviving instance only.

    The user asked for single-representative previews with html truncated
    past ``HTML_PREVIEW_LIMIT`` chars. Showing every instance per chunk
    on a 50-card grid floods the console; one is enough to see what the
    chunk actually captures.
    """
    _banner("First instance of each chunk (html truncated at 256 chars)")
    by_chunk: Dict[str, List[Any]] = defaultdict(list)
    for inst in result.instances:
        by_chunk[inst.chunk_id].append(inst)

    for chunk in result.chunks:
        group = by_chunk.get(chunk.chunk_id, [])
        if not group:
            continue
        inst = sorted(group, key=lambda r: r.instance_idx)[0]
        print(f"\n[Chunk] pattern={chunk.pattern!r}")
        print(f"  members={len(chunk.member_xpaths)}  "
              f"rendered={len(group)}  "
              f"char_count={chunk.char_count}")
        print(f"  first instance @ {inst.absolute_xpath}")
        # Content-structure summary — the format the SLM / GUI will see.
        # Top-down recursive chunking emits at whichever pattern-trie
        # level fits the token budget, so inspecting these lines is the
        # direct way to tell "am I looking at a card chunk or did the
        # chunker overshoot into a page-level rollup?".
        fields = getattr(inst, "fields", {}) or {}
        if fields:
            print("    content-structure summary:")
            for key, vals in fields.items():
                print(f"      {key}: {vals}")
        print(f"    embed-text: {_truncate(inst.rendered_text, HTML_PREVIEW_LIMIT)!r}")
        print(f"    html:       {_truncate(inst.html_raw, HTML_PREVIEW_LIMIT)!r}")


# ---------------------------------------------------------------------------
# Content-distilled augmented graph
# ---------------------------------------------------------------------------


def build_content_graphs(
    content_tree: Dict[str, Any],
) -> Tuple[nx.DiGraph, nx.Graph, str, Dict[str, str]]:
    """Build the two graphs every algorithm needs from the *distilled* tree.

    * ``T`` (DiGraph) — pure parent→child tree. Used by Strahler, Sackin,
      Colless, Sarkar Poincaré, and the tree-shaped Weisfeiler-Leman
      bottom-up colouring. Edges carry ``edge_type='parent_child'``
      because ``tree_metrics`` filters on that key.

    * ``G`` (Graph, undirected) — augmented graph with:
        - parent-child edges (tree backbone)
        - sibling edges (dense local cohorts, help HKS localize)
        - cross-pattern edges (cliques between nodes that share a
          generalized xpath — tells spectral/GDV about structural
          repetition)
      This mirrors ``backend.augmented_graph.build_augmented_nx``.

    CRITICAL: both graphs are built over ``content_tree`` — the
    Patricia-collapsed, content-only distillation — never the raw DOM.
    That's the entire point of the distillation step upstream.
    """
    T = nx.DiGraph()
    G = nx.Graph()
    xpath_to_id: Dict[str, str] = {}
    patterns_by_id: Dict[str, str] = {}

    counter = [0]

    def _mk() -> str:
        counter[0] += 1
        return f"n{counter[0]}"

    root_id = _mk()
    T.add_node(root_id, xpath="/", pattern="/", tag="root", depth=0)
    G.add_node(root_id, xpath="/", pattern="/", tag="root", depth=0)
    patterns_by_id[root_id] = "/"
    xpath_to_id["/"] = root_id

    def _walk(node: Dict[str, Any], parent_id: str, depth: int) -> List[str]:
        sibling_ids: List[str] = []
        for key, child in node.items():
            if key.startswith("_") or not isinstance(child, dict):
                continue
            xp = child.get("_xpath", key)
            pat = generalize_xpath(xp)
            tag = xp.rstrip("/").split("/")[-1].split("[")[0] or "root"
            nid = _mk()
            attrs = dict(xpath=xp, pattern=pat, tag=tag, depth=depth + 1,
                         is_content=("_content" in child))
            T.add_node(nid, **attrs)
            G.add_node(nid, **attrs)
            T.add_edge(parent_id, nid, edge_type="parent_child")
            G.add_edge(parent_id, nid, edge_type="parent_child")
            xpath_to_id[xp] = nid
            patterns_by_id[nid] = pat
            sibling_ids.append(nid)
            _walk(child, nid, depth + 1)

        # Sibling edges live only in the undirected augmented graph.
        for i in range(len(sibling_ids)):
            for j in range(i + 1, len(sibling_ids)):
                G.add_edge(sibling_ids[i], sibling_ids[j], edge_type="sibling")
        return sibling_ids

    _walk(content_tree, root_id, 0)

    # Cross-pattern clique edges (one clique per generalized xpath).
    pattern_groups: Dict[str, List[str]] = defaultdict(list)
    for nid, pat in patterns_by_id.items():
        pattern_groups[pat].append(nid)
    for pat, members in pattern_groups.items():
        if len(members) > 1:
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    G.add_edge(members[i], members[j],
                               edge_type="cross_pattern")

    return T, G, root_id, xpath_to_id


# ---------------------------------------------------------------------------
# Weisfeiler-Leman bottom-up colouring (tree version)
# ---------------------------------------------------------------------------


def wl_bottom_up_colors(
    T: nx.DiGraph, root: str, k_iters: int = 3,
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Compute WL hashes on the content-distilled tree.

    We use the bottom-up variant (the only form that's well-defined on
    rooted trees without the neighbour-symmetry ambiguity of general-
    graph WL): each node's colour is a hash of ``(tag, sorted(children
    colours))``. Iterated ``k_iters`` times so a node's signature
    eventually captures its subtree up to depth ``k_iters``.

    Returns ``(color, group_size)``: two nodes with the same colour have
    structurally identical subtrees up to depth ``k_iters``.
    """
    # Initial colour: just the tag.
    colors: Dict[str, int] = {
        n: hash(T.nodes[n].get("tag", "?")) & 0xFFFFFFFF for n in T.nodes
    }
    for _ in range(k_iters):
        new_colors: Dict[str, int] = {}
        for n in T.nodes:
            child_colors = sorted(colors[c] for c in T.successors(n))
            sig = hash((colors[n], tuple(child_colors))) & 0xFFFFFFFF
            new_colors[n] = sig
        colors = new_colors

    counts = Counter(colors.values())
    group_size = {n: counts[c] for n, c in colors.items()}
    return colors, group_size


# ---------------------------------------------------------------------------
# Per-instance feature assembly (with written heuristic reasoning)
# ---------------------------------------------------------------------------


def _print_heuristic_reasoning(T: nx.DiGraph, G: nx.Graph) -> None:
    """Print the per-algorithm hyperparameter reasoning before we run."""
    depths = [T.nodes[n].get("depth", 0) for n in T.nodes]
    max_depth = max(depths) if depths else 0
    mean_deg_G = float(np.mean([d for _, d in G.degree()])) if G.nodes else 0.0

    _banner("Heuristic reasoning -- parameters chosen for THIS distilled graph")
    print(f"  Distilled tree: |V|={T.number_of_nodes()}, "
          f"|E|={T.number_of_edges()}, max_depth={max_depth}")
    print(f"  Augmented graph: |V|={G.number_of_nodes()}, "
          f"|E|={G.number_of_edges()}, mean_deg={mean_deg_G:.2f}")

    print("\n  (1) Weisfeiler-Leman iterations k=3")
    print("      Why: content-distilled subtrees are shallow (typically "
          "<=6-8 deep). k=3 captures a 'subtree up to depth 3' signature "
          "-- exactly the radius at which a product card (h2/p/img) "
          "becomes distinguishable from a nav link (bare <a>). Higher k "
          "gives diminishing returns and blows up the hash-group lattice.")

    print("\n  (2) Heat Kernel Signature times t = [0.1, 1.0, 10.0]")
    print("      Why: three decades of diffusion span the relevant scales.")
    print("      t=0.1 -> almost-local (2-hop neighbourhood -- card-level).")
    print("      t=1.0 -> mid-range mixing (across sibling/cross-pattern "
          "cliques -- grid-level).")
    print("      t=10 -> near-stationary (page-level role). Past the "
          "mixing time of an augmented graph of this size, so adding a "
          "fourth time adds no variance.")

    print("\n  (3) Sarkar Poincaré tau=0.4")
    print("      Why: Sarkar's minimum faithful tau for a tree of max "
          "degree d is tau* = (1/2)*log((1+sin(pi/d))/(1-sin(pi/d))). "
          "For d<=12 (typical sibling count after distillation), "
          "tau*~0.28; we pick 0.4 for a small safety margin. That "
          "places R=tanh(tau/2)~=0.20 per hop, so a 6-deep tree fills "
          "the disk without saturating the boundary -- we keep euclidean "
          "distances meaningful as a feature.")

    print("\n  (4) Growth dimension max_hops=3 (dropped in favour of HKS)")
    print("      Why dropped: on the distilled augmented graph the "
          "growth curve saturates almost immediately because cross-"
          "pattern cliques let every node reach the whole page in ~3 "
          "hops. HKS already encodes this at multiple scales without "
          "the log-regression noise. We keep Strahler for the pure-tree "
          "complexity signal instead.")

    print("\n  (5) Graphlet Degree Vector orbits 0-7 (size<=4)")
    print("      Why: orbit 3 (triangle) fires on nodes that share a "
          "cross-pattern clique AND are siblings -- i.e. 'part of a "
          "repeating local cohort'. Orbit 5 (4-star centre) fires on "
          "hub-like pattern representatives. Both are exactly the "
          "signals we want to separate 'one of many cards' from 'unique "
          "hero'. Size <=4 is the highest size with closed-form O(E*d) "
          "counting -- size 5 would cost us the interactive demo "
          "latency budget.")

    print("\n  (6) DBSCAN min_samples=4, eps from k-distance knee, PCA->12d")
    print("      Why min_samples=4: DBSCAN's rule of thumb is "
          "min_samples ~ 2*dim, but with PCA-reduced 12 dims and "
          "typically <100 instances per page, 2*dim=24 would label "
          "everything as noise. min_samples=4 keeps clusters formable "
          "while still rejecting isolated outliers.")
    print("      Why eps from knee: the k=min_samples-1 distance sorted "
          "plot's elbow is the classic Ester et al. heuristic -- picks "
          "the density level that separates core points from noise "
          "WITHOUT hand-tuning. We detect it as the point of maximum "
          "curvature on the sorted curve.")

    print("\n  (7) Tree kernels: ST(decay=0.5), SST(lambda=0.4), "
          "PT(lambda=0.3, mu=0.5)")
    print("      Why three kernels: ST (exact subtrees), SST (contiguous "
          "partial subtrees), PT (non-contiguous subsets) encode "
          "progressively looser notions of 'how repeatable is this "
          "subtree'. Their pairwise correlation on our data is 0.4-0.7, "
          "so PCA finds 2-3 orthogonal axes from them.")
    print("      Decay choices 0.5/0.4/0.3 mirror the Collins-Duffy "
          "standards: tighter decays for looser kernels keep kernel "
          "values numerically stable at depth 8.")

    print("\n  (8) SGWT scales=[1.0,2.0,4.0], Chebyshev K=4")
    print("      Why: SGWT's exp(-s*lambda) kernel gives a 'second "
          "opinion' on the same eigendecomposition HKS uses -- cluster "
          "separation shouldn't hinge on HKS alone. Scales 1/2/4 sit "
          "between HKS's mid and boundary regimes. Chebyshev K=4 over "
          "the rescaled Laplacian on the degree signal is the standard "
          "short-range filter bank; we keep T_1..T_3 to avoid triple-"
          "counting the degree.")

    print("\n  (9) Forman-Ricci mean per node (Ollivier-Ricci skipped)")
    print("      Why Forman: closed-form O(|E|*d); captures 'am I a "
          "bridge' (negative) vs. 'am I inside a clique' (positive). "
          "Ollivier-Ricci was skipped -- its all-pairs shortest-path "
          "table is O(V^2*d) and gives no additional separation on a "
          "graph with sibling+clique augmentation.")

    print("\n  (10) DAG compression (sharing, compression_ratio, depth)")
    print("      Why: bottom-up structural hash merges identical "
          "subtrees; compression_ratio >1 surfaces exactly the "
          "'repeating cohort' signal we want to separate cards from "
          "unique chrome. No free parameter.")

    print("\n  (11) Path decomp: HLD chain_pos, centroid_level, euler_in")
    print("      Why: HLD chain_pos tracks heavy-spine depth "
          "(sidebars become a single chain). Centroid level is "
          "unbalance-invariant. Euler_in is the document-order stand-"
          "in, normalized by 2N to be page-size-invariant. euler_out "
          "is dropped -- perfectly correlated with euler_in+subtree.")

    print("\n  (12) WL multiplicity spectrum, heritage_depth_match, "
          "Dirichlet energy")
    print("      Why: three complementary 'how unique am I' signals. "
          "WL multiplicity: post-k-refinement class size. Heritage "
          "match: count of nodes sharing exact root-to-here tag path "
          "-- stricter than sibling homogeneity. Dirichlet energy on "
          "the depth signal: fires when sibling/cross-pattern edges "
          "shortcut deep subtrees.")

    print("\n  (13) Graph-level broadcast: Fiedler, Betti b0, b1")
    print("      Why broadcast: a DBSCAN row lives per-instance but "
          "the *page-level* topology (well-mixed? many cycles?) is a "
          "context feature. Fiedler=algebraic connectivity, b0=#cc, "
          "b1=E-V+b0. Same value on every row of the same page.")


def build_instance_feature_matrix(
    result, T: nx.DiGraph, G: nx.Graph, root: str, xpath_to_id: Dict[str, str],
) -> Tuple[np.ndarray, List[str], List[Any]]:
    """Compute the [n_instances, n_features] matrix.

    For each non-empty ChunkInstance we look up the Patricia node that
    owns its ``absolute_xpath``. When the rendered instance's xpath is
    below the distilled trie depth (which happens for deeply-nested
    renders — the distillation collapses single-child chains), we walk
    up the xpath's parent segments until we find a node in the tree.
    The feature is then the union of that node's tree/spectral/embed
    signatures.
    """
    def _safe(fn, fallback, label):
        try:
            return fn()
        except Exception as exc:
            logger.warning("%s failed (%s) -- using fallback", label, exc)
            return fallback

    strahler = StrahlerAlgorithm.compute_strahler(T, root)
    sackin, colless = TreeBalanceAlgorithms.compute_sackin_index(T, root)
    n_leaves = sum(1 for n in T.nodes if T.out_degree(n) == 0)
    sackin_z = TreeBalanceAlgorithms.compute_balance_zscore(sackin, n_leaves)

    _, wl_group = wl_bottom_up_colors(T, root, k_iters=3)

    # --- Structural basics (§12.8.1, §12.8.2, §12.8.3) ---
    subtree_sizes = StructuralAlgorithms.compute_subtree_sizes(T, root)
    branching = StructuralAlgorithms.compute_branching_factors(T)
    sibling_rank = StructuralAlgorithms.compute_sibling_ranks(T)
    wl_hashes_for_freq = {n: c for n, c in wl_group.items()}  # reuse WL colors
    pattern_freq = FrequencyAlgorithms.compute_pattern_frequency(
        T, wl_hashes_for_freq,
    )
    sibling_homog = FrequencyAlgorithms.compute_sibling_homogeneity(T)
    content_type_ent = InformationTheoreticAlgorithms.compute_content_type_entropy(T)
    attr_ent = InformationTheoreticAlgorithms.compute_attr_entropy(T)

    # --- Cohesive (§12.8.11) ---
    k_core = _safe(lambda: CohesiveAlgorithms.compute_k_core(G),
                   {str(n): 0 for n in G.nodes}, "k_core")
    triangles = _safe(lambda: CohesiveAlgorithms.compute_triangle_count(G),
                      {str(n): 0 for n in G.nodes}, "triangles")
    clustering = _safe(lambda: CohesiveAlgorithms.compute_clustering_coefficient(G),
                       {str(n): 0.0 for n in G.nodes}, "clustering")
    articulation = _safe(lambda: CohesiveAlgorithms.compute_articulation_points(G),
                         {str(n): False for n in G.nodes}, "articulation")
    bridges = _safe(lambda: CohesiveAlgorithms.compute_bridge_count(G),
                    {str(n): 0 for n in G.nodes}, "bridges")

    # --- Centrality (§12.8.7) ---
    betweenness = _safe(lambda: CentralityAlgorithms.compute_betweenness(G),
                        {n: 0.0 for n in G.nodes}, "betweenness")
    closeness = _safe(lambda: CentralityAlgorithms.compute_closeness(G),
                      {n: 0.0 for n in G.nodes}, "closeness")
    pagerank = _safe(lambda: CentralityAlgorithms.compute_pagerank(T),
                     {n: 0.0 for n in T.nodes}, "pagerank")

    # --- Curvature (§12.8.16) ---
    forman_edges = _safe(lambda: CurvatureSignatures.compute_forman_ricci(G),
                         {}, "forman_ricci")
    forman_node: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for (u, v), f in forman_edges.items():
        counts[u] = counts.get(u, 0) + 1
        counts[v] = counts.get(v, 0) + 1
        forman_node[u] = forman_node.get(u, 0.0) + f
        forman_node[v] = forman_node.get(v, 0.0) + f
    for n in G.nodes:
        c = counts.get(n, 0)
        forman_node[n] = forman_node.get(n, 0.0) / max(c, 1)

    # --- Topological tree invariants (§12.8.9, §12.8.17) ---
    depth_range = _safe(lambda: TopologicalFeatures.compute_depth_range(T, root),
                        {n: 0 for n in T.nodes}, "depth_range")
    path_var = _safe(lambda: TopologicalFeatures.compute_path_length_var(T, root),
                     {n: 0.0 for n in T.nodes}, "path_length_var")
    level_w = _safe(lambda: TopologicalFeatures.compute_level_width(T, root),
                    {n: 1 for n in T.nodes}, "level_width")
    tree_d = _safe(lambda: AlgebraicInvariants.compute_tree_depth(T, root),
                   {n: 0 for n in T.nodes}, "tree_depth")
    # Prüfer wants an undirected tree; fall back silently on non-trees.
    prufer = _safe(lambda: AlgebraicInvariants.compute_prufer_sequence_index(T, root),
                   {n: 0 for n in T.nodes}, "prufer")
    n_nodes = max(T.number_of_nodes(), 1)

    # --- Path decomposition (§12.8.10) ---
    chain_id, chain_pos = _safe(
        lambda: PathDecompositionAlgorithms.compute_hld(T, root, subtree_sizes),
        ({n: 0 for n in T.nodes}, {n: 0 for n in T.nodes}), "hld")
    centroid_level, _ = _safe(
        lambda: PathDecompositionAlgorithms.compute_centroid_decomposition(
            T, root, subtree_sizes),
        ({n: 0 for n in T.nodes}, {n: 0 for n in T.nodes}), "centroid")
    euler_in, _ = _safe(
        lambda: PathDecompositionAlgorithms.compute_euler_tour(T, root),
        ({n: 0 for n in T.nodes}, {n: 0 for n in T.nodes}), "euler_tour")

    # --- Tree kernels (§12.8.12) ---
    st_kernel = _safe(lambda: TreeKernels.compute_subtree_kernel(T, root, decay=0.5),
                      {n: 0.0 for n in T.nodes}, "st_kernel")
    sst_kernel = _safe(lambda: TreeKernels.compute_subset_tree_kernel(T, root, lambda_decay=0.4),
                       {n: 0.0 for n in T.nodes}, "sst_kernel")
    pt_kernel = _safe(lambda: TreeKernels.compute_partial_tree_kernel(T, root, lambda_decay=0.3, mu=0.5),
                      {n: 0.0 for n in T.nodes}, "pt_kernel")

    # --- Heat Kernel Signature over the augmented graph ---
    try:
        hks = SpectralSignatures.compute_hks(G, times=[0.1, 1.0, 10.0])
    except Exception as exc:
        logger.warning("HKS failed (%s) -- filling zeros", exc)
        hks = np.zeros((G.number_of_nodes(), 3))
    g_nodes_order = list(G.nodes)
    hks_by_id = {nid: hks[i] for i, nid in enumerate(g_nodes_order)}

    # --- Spectral Graph Wavelets (§12.8.20) ---
    try:
        sgwt_mat = SpectralGraphWavelets.compute_sgwt(G, scales=[1.0, 2.0, 4.0])
    except Exception as exc:
        logger.warning("SGWT failed (%s)", exc)
        sgwt_mat = np.zeros((len(g_nodes_order), 3))
    sgwt_by_id = {nid: sgwt_mat[i] for i, nid in enumerate(g_nodes_order)}

    # --- Chebyshev filters (§12.8.13), keep T_1..T_3 ---
    try:
        cheb_mat = SpectralSignatures.compute_chebyshev_features(G, K=4)
    except Exception as exc:
        logger.warning("Chebyshev failed (%s)", exc)
        cheb_mat = np.zeros((len(g_nodes_order), 5))
    cheb_by_id = {nid: cheb_mat[i] for i, nid in enumerate(g_nodes_order)}

    # --- Sarkar Poincaré on the tree ---
    try:
        pcoords = HyperbolicEmbeddings.sarkar_poincare(T, root, tau=0.4, dim=2)
    except Exception as exc:
        logger.warning("Sarkar failed (%s)", exc)
        pcoords = {n: [0.0, 0.0] for n in T.nodes}
    distortion = _safe(
        lambda: HyperbolicEmbeddings.compute_poincare_distortion(T, root, pcoords),
        {n: 0.0 for n in T.nodes}, "poincare_distortion")
    lorentz = _safe(
        lambda: HyperbolicEmbeddings.poincare_to_lorentz(pcoords),
        {n: [1.0, 0.0, 0.0] for n in T.nodes}, "poincare_to_lorentz")

    # --- Graphlet Degree Vectors (8 orbits) ---
    try:
        gdv = GraphletDegreeVector.compute_gdv(G, max_size=4)
    except Exception as exc:
        logger.warning("GDV failed (%s)", exc)
        gdv = {n: [0] * 8 for n in G.nodes}

    # --- DAG compression (§12.8.24) ---
    dag_sharing, dag_compress, dag_depth = _safe(
        lambda: DAGCompressionAlgorithms.compute_dag_sharing(T, root),
        ({n: 1 for n in T.nodes},
         {n: 1.0 for n in T.nodes},
         {n: 0 for n in T.nodes}),
        "dag_compression")

    # --- Ancestry (§12.8.23) ---
    heritage_match = _safe(
        lambda: AncestryProfile.compute_heritage_depth_match(T, root),
        {n: 1 for n in T.nodes}, "heritage")

    # --- Local Total Variation / Dirichlet energy (§12.8.28) ---
    _, dirichlet = _safe(
        lambda: LocalTotalVariation.compute_boundary_signature(G, signal_attr="depth"),
        ({n: [] for n in G.nodes}, {n: 0.0 for n in G.nodes}), "dirichlet")

    # --- WL multiplicity spectrum (§12.8.18), keep last iter ---
    wl_spec = _safe(
        lambda: WLMultiplicitySpectrum.compute_wl_spectrum(G, iterations=3),
        {n: [1, 1, 1] for n in G.nodes}, "wl_multiplicity")

    # --- Graph-level scalars broadcast to every row ---
    fiedler = _safe(lambda: SpectralAlgorithms.compute_fiedler_value(G), 0.0,
                    "fiedler")
    try:
        b0, b1 = TopologicalSignatures.compute_betti_numbers(G)
    except Exception:
        b0, b1 = 1, 0

    def _lookup_id(xp: str) -> Optional[str]:
        """Find the closest ancestor distilled-tree node for an xpath."""
        if xp in xpath_to_id:
            return xpath_to_id[xp]
        # Walk up absolute xpath one segment at a time.
        parts = xp.strip("/").split("/")
        for k in range(len(parts) - 1, 0, -1):
            anc = "/" + "/".join(parts[:k])
            if anc in xpath_to_id:
                return xpath_to_id[anc]
        return None

    def _flt(d, key, default=0.0):
        v = d.get(key, default)
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(default)

    rows: List[List[float]] = []
    kept_instances: List[Any] = []
    for inst in result.instances:
        nid = _lookup_id(inst.absolute_xpath)
        if nid is None:
            continue
        depth_raw = T.nodes[nid].get("depth", 0)

        pc = pcoords.get(nid, [0.0, 0.0])
        px, py = float(pc[0]), float(pc[1])
        prad = math.hypot(px, py)
        lor = lorentz.get(nid, [1.0, 0.0, 0.0])
        lor_x0 = float(lor[0]) if lor else 1.0

        gdv_vec = gdv.get(nid, [0] * 8)
        gdv_vec = [math.log1p(max(v, 0)) for v in gdv_vec]
        hks_vec = hks_by_id.get(nid, np.zeros(3))
        sgwt_vec = sgwt_by_id.get(nid, np.zeros(3))
        cheb_vec = cheb_by_id.get(nid, np.zeros(5))
        wl_last = wl_spec.get(nid, [1, 1, 1])
        wl_last_val = float(wl_last[-1]) if wl_last else 1.0

        feat = [
            # --- tree balance / complexity ---
            float(strahler.get(nid, 1)),
            float(sackin_z.get(nid, 0.0)),
            math.log1p(float(colless.get(nid, 0))),
            math.log1p(float(wl_group.get(nid, 1))),
            # --- structural basics ---
            math.log1p(float(subtree_sizes.get(nid, 1))),
            float(branching.get(nid, 0)),
            float(sibling_rank.get(nid, 0)),
            float(sibling_homog.get(nid, 1.0)),
            float(content_type_ent.get(nid, 0.0)),
            float(attr_ent.get(nid, 0.0)),
            math.log1p(float(pattern_freq.get(nid, 1))),
            # --- cohesive ---
            _flt(k_core, nid) if nid in k_core else _flt(k_core, str(nid)),
            math.log1p(_flt(triangles, nid) if nid in triangles
                       else _flt(triangles, str(nid))),
            _flt(clustering, nid) if nid in clustering
                else _flt(clustering, str(nid)),
            1.0 if (articulation.get(nid, articulation.get(str(nid), False))) else 0.0,
            _flt(bridges, nid) if nid in bridges else _flt(bridges, str(nid)),
            # --- centrality ---
            math.log1p(float(betweenness.get(nid, 0.0))),
            float(closeness.get(nid, 0.0)),
            float(pagerank.get(nid, 0.0)),
            # --- curvature ---
            float(forman_node.get(nid, 0.0)),
            # --- topological tree invariants ---
            float(depth_range.get(nid, 0)),
            float(path_var.get(nid, 0.0)),
            math.log1p(float(level_w.get(nid, 1))),
            float(tree_d.get(nid, 0)),
            float(prufer.get(nid, 0)) / float(n_nodes),
            # --- path decomposition ---
            math.log1p(float(chain_pos.get(nid, 0))),
            # Centroid-decomposition recursion depth is O(log N) in
            # theory; the current implementation re-passes sibling
            # sets and can blow to ~150 on real pages. log1p + clip
            # to 20 ensures it contributes ~ log N of signal without
            # dominating the feature bank.
            min(math.log1p(float(centroid_level.get(nid, 0))), 20.0),
            float(euler_in.get(nid, 0)) / float(2 * n_nodes),
            # --- tree kernels (log to tame products) ---
            math.log1p(float(st_kernel.get(nid, 0.0))),
            math.log1p(float(sst_kernel.get(nid, 0.0))),
            math.log1p(float(pt_kernel.get(nid, 0.0))),
            # --- spectral ---
            float(hks_vec[0]), float(hks_vec[1]), float(hks_vec[2]),
            float(sgwt_vec[0]), float(sgwt_vec[1]), float(sgwt_vec[2]),
            float(cheb_vec[1]), float(cheb_vec[2]), float(cheb_vec[3]),
            # --- hyperbolic embedding ---
            px, py, prad,
            float(distortion.get(nid, 0.0)),
            math.log1p(max(lor_x0 - 1.0, 0.0)),
            # --- graphlets ---
            *gdv_vec,
            # --- DAG compression ---
            math.log1p(float(dag_sharing.get(nid, 1))),
            float(dag_compress.get(nid, 1.0)),
            float(dag_depth.get(nid, 0)),
            # --- ancestry / LTV / WL multiplicity ---
            math.log1p(float(heritage_match.get(nid, 1))),
            math.log1p(float(dirichlet.get(nid, 0.0))),
            math.log1p(wl_last_val),
            # --- graph-level broadcast ---
            float(fiedler),
            float(b0),
            math.log1p(float(b1)),
            # --- anchors ---
            float(depth_raw),
            math.log1p(float(len(inst.html_raw or ""))),
        ]
        rows.append(feat)
        kept_instances.append(inst)

    names = [
        # tree balance / complexity
        "strahler", "sackin_z", "log_colless", "log_wl_group",
        # structural basics
        "log_subtree_size", "branching", "sibling_rank",
        "sibling_homog", "content_type_ent", "attr_ent",
        "log_pattern_freq",
        # cohesive
        "k_core", "log_triangles", "clustering_coef",
        "is_articulation", "bridge_count",
        # centrality
        "log_betweenness", "closeness", "pagerank",
        # curvature
        "forman_mean",
        # topological tree invariants
        "depth_range", "path_length_var", "log_level_width",
        "tree_depth", "prufer_norm",
        # path decomposition
        "log_chain_pos", "centroid_level", "euler_in_norm",
        # tree kernels
        "log_st_kernel", "log_sst_kernel", "log_pt_kernel",
        # spectral
        "hks_t0.1", "hks_t1.0", "hks_t10",
        "sgwt_s1", "sgwt_s2", "sgwt_s4",
        "cheb_T1", "cheb_T2", "cheb_T3",
        # hyperbolic
        "poincare_x", "poincare_y", "poincare_r",
        "poincare_distortion", "log_lorentz_x0",
        # graphlets
        "gdv0_edge", "gdv1_path_ctr", "gdv2_path_end", "gdv3_triangle",
        "gdv4_4path", "gdv5_star_ctr", "gdv6_4cycle", "gdv7_simto_mean",
        # DAG compression
        "log_dag_sharing", "dag_compression", "dag_depth",
        # ancestry / LTV / WL multiplicity
        "log_heritage_match", "log_dirichlet_energy", "log_wl_multiplicity",
        # graph-level broadcast
        "fiedler", "betti_0", "log_betti_1",
        # anchors
        "depth", "log_html_chars",
    ]
    X = np.array(rows, dtype=np.float32) if rows else np.zeros((0, len(names)))
    return X, names, kept_instances


# ---------------------------------------------------------------------------
# DBSCAN orchestration with empirical eps selection
# ---------------------------------------------------------------------------


def pick_eps_from_knee(X: np.ndarray, min_samples: int) -> Tuple[float, np.ndarray]:
    """Return (eps, sorted k-distance curve).

    The k-distance knee is the canonical Ester et al. heuristic: compute
    each point's distance to its k-th nearest neighbour (k = min_samples
    - 1), sort ascending, and take the point of maximum second-
    difference as the elbow. Below the elbow: dense core points; above:
    outliers. That elbow is the eps that splits "core" from "noise".
    """
    k = max(min_samples - 1, 1)
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    dists, _ = nn.kneighbors(X)
    kdist = np.sort(dists[:, -1])
    if len(kdist) < 4:
        return float(np.median(kdist) + 1e-3), kdist

    # Discrete curvature via second difference.
    d2 = np.diff(kdist, n=2)
    knee_idx = int(np.argmax(d2)) + 1  # +1 because np.diff shifts indices
    eps = float(kdist[knee_idx])
    if not math.isfinite(eps) or eps <= 0:
        eps = float(np.median(kdist) + 1e-3)
    return eps, kdist


def run_instance_dbscan(
    X: np.ndarray, min_samples: int = 4,
) -> Tuple[np.ndarray, float, np.ndarray]:
    """Scale, PCA-denoise, k-distance-eps, then DBSCAN on cuML if available.

    Returns ``(labels, eps, kdist_curve)``.
    """
    if len(X) < min_samples + 1:
        return np.full(len(X), -1), 0.0, np.zeros(0)

    # RobustScaler (median / IQR) rather than StandardScaler so that a
    # single blown-up feature (Chebyshev T_k values at +/-70, centroid
    # level jumping past 100 on deep trees) can't crush the rest of the
    # feature bank. Winsorize to +/- 6 IQR to hard-cap any remaining
    # outliers — the tarot run had ~20 features with tails worse than
    # this and eps blew up to 23+.
    Xs = RobustScaler(quantile_range=(10.0, 90.0)).fit_transform(X)
    Xs = np.clip(Xs, -6.0, 6.0)

    # PCA to ~12 dims: drops co-linear features (e.g. HKS/SGWT share an
    # eigendecomposition; ST/SST/PT kernels are ~0.5 correlated; GDV
    # orbits covary for leaves). 12 was chosen so >=95% of variance
    # typically survives on the ~60-column feature bank while keeping
    # DBSCAN's euclidean metric in a low-dim regime where eps has a
    # stable scale. Falls back to full dims if N<12.
    n_components = min(12, Xs.shape[1], Xs.shape[0] - 1)
    Xp = PCA(n_components=n_components, random_state=42).fit_transform(Xs)

    eps, kdist = pick_eps_from_knee(Xp, min_samples=min_samples)

    if USE_CUML:
        logger.info(
            "DBSCAN on cuML/cuPy (eps=%.4f, min_samples=%d, dim=%d, N=%d)",
            eps, min_samples, Xp.shape[1], Xp.shape[0],
        )
        labels = cuDBSCAN(
            eps=eps, min_samples=min_samples,
        ).fit_predict(Xp.astype(np.float32))
        labels = np.asarray(labels)
    else:
        logger.info(
            "DBSCAN on sklearn (cuML unavailable) eps=%.4f min_samples=%d",
            eps, min_samples,
        )
        labels = skDBSCAN(
            eps=eps, min_samples=min_samples,
        ).fit_predict(Xp)

    return labels, eps, kdist


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def plot_kdist(kdist: np.ndarray, eps: float, out_path: str) -> None:
    if len(kdist) < 2:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(kdist, linewidth=1.4)
    ax.axhline(eps, color="crimson", linestyle="--",
               label=f"chosen eps = {eps:.3f}")
    ax.set_title("k-distance knee -> chosen DBSCAN eps")
    ax.set_xlabel("points sorted by k-th nearest-neighbour distance")
    ax.set_ylabel("distance")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_feature_variance(
    X: np.ndarray, names: List[str], out_path: str,
) -> None:
    if len(X) == 0:
        return
    Xs = StandardScaler().fit_transform(X)
    var = Xs.var(axis=0)
    order = np.argsort(var)[::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(range(len(var)), var[order])
    ax.set_xticks(range(len(var)))
    ax.set_xticklabels([names[i] for i in order], rotation=60, ha="right")
    ax.set_title("Per-feature variance after StandardScaler "
                 "(should hover ~1; outliers signal heavy tails)")
    ax.set_ylabel("variance")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_dbscan_pca(
    X: np.ndarray, labels: np.ndarray, eps: float, out_path: str,
) -> None:
    if len(X) < 3:
        return
    Xs = StandardScaler().fit_transform(X)
    n_comp = min(3, Xs.shape[1])
    P = PCA(n_components=n_comp, random_state=42).fit_transform(Xs)
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    uniq = sorted(set(labels))
    cmap = plt.get_cmap("tab20")
    for k in uniq:
        mask = labels == k
        lbl = "noise" if k == -1 else f"C{k}"
        color = (0.3, 0.3, 0.3) if k == -1 else cmap(k % 20)
        if P.shape[1] >= 3:
            ax.scatter(P[mask, 0], P[mask, 1], P[mask, 2],
                       c=[color], s=32, alpha=0.85,
                       edgecolor="k", label=lbl)
        else:
            ax.scatter(P[mask, 0], P[mask, 1], np.zeros(mask.sum()),
                       c=[color], s=32, alpha=0.85, label=lbl)
    n_clusters = len(uniq) - (1 if -1 in uniq else 0)
    ax.set_title(f"DBSCAN over instance feature vectors "
                 f"(eps={eps:.3f}, clusters={n_clusters}, "
                 f"noise={int((labels == -1).sum())})")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_zlabel("PC3")
    ax.legend(loc="upper left", bbox_to_anchor=(1.05, 1))
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def summarize_clusters(
    labels: np.ndarray, kept_instances: List[Any], X: np.ndarray,
    names: List[str],
) -> None:
    if len(labels) == 0:
        print("\n(no instances to summarize)")
        return

    _banner("DBSCAN cluster summary")
    counts = Counter(labels.tolist())
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int(counts.get(-1, 0))
    print(f"  instances: {len(labels)}  clusters: {n_clusters}  noise: {n_noise}")
    print(f"  size distribution: "
          + ", ".join(f"C{k}:{v}" for k, v in counts.most_common() if k != -1))

    if n_clusters >= 2 and n_noise < len(labels):
        try:
            Xs = StandardScaler().fit_transform(X)
            s = silhouette_score(Xs, labels)
            print(f"  silhouette score: {s:+.3f}  "
                  "(1.0 perfect / 0.0 overlapping / negative = mislabeled)")
        except Exception as exc:
            logger.warning("silhouette failed: %s", exc)

    # Per-cluster: representative instance + per-feature cluster means.
    for label in sorted(set(labels)):
        idxs = np.where(labels == label)[0]
        name = "noise" if label == -1 else f"C{label}"
        rep = kept_instances[idxs[0]]
        print(f"\n  [{name}]  size={len(idxs)}  "
              f"representative xpath={rep.absolute_xpath}")
        print(f"    pattern: {rep.pattern}")
        print(f"    html:    {_truncate(rep.html_raw, HTML_PREVIEW_LIMIT)!r}")

        if len(idxs) >= 2:
            # Print TWO orderings:
            #   - top-10 by |cluster mean|           -- what's loud in THIS cluster
            #   - top-10 by |z(cluster mean)|        -- what DISTINGUISHES this
            #     cluster from the rest of the dataset (silly to rank a
            #     cluster of 'high triangle_count' items by mean triangles
            #     if every other cluster is also high).
            cmean = X[idxs].mean(axis=0)
            gmean = X.mean(axis=0)
            gstd = X.std(axis=0) + 1e-9
            zscore = (cmean - gmean) / gstd

            top_raw = np.argsort(-np.abs(cmean))[:10]
            top_z = np.argsort(-np.abs(zscore))[:10]
            parts_raw = [f"{names[i]}={cmean[i]:.2f}" for i in top_raw]
            parts_z = [f"{names[i]}(z={zscore[i]:+.2f})" for i in top_z]
            print(f"    top-10 mean features:     {', '.join(parts_raw)}")
            print(f"    top-10 distinguishing:    {', '.join(parts_z)}")


# ---------------------------------------------------------------------------
# UMAP scatter (kept from the original demo; diagnostic only)
# ---------------------------------------------------------------------------


def umap_scatter_from_db(conn, *, output_path: str = "umap_chunks.png") -> None:
    try:
        import umap
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except Exception as exc:
        logger.warning("UMAP demo skipped (%s)", exc)
        return

    rows = load_all_instances(conn)
    if len(rows) < 4:
        logger.info("UMAP skipped -- need >=4 rows, got %d", len(rows))
        return

    X = np.asarray([r.embedding for r in rows], dtype=np.float32)
    if X.ndim != 2 or X.shape[1] != 768:
        logger.warning("UMAP: unexpected embedding shape %s", X.shape)
        return

    n_rows = X.shape[0]
    target_components = 6 if n_rows >= 8 else 3
    n_neighbors = min(15, max(2, n_rows - 1))
    reducer = umap.UMAP(
        n_components=target_components, n_neighbors=n_neighbors,
        metric="cosine", random_state=42,
    )
    Y = reducer.fit_transform(X)
    xyz = Y[:, :3]
    if target_components == 6:
        rgb = Y[:, 3:]
        mn = rgb.min(axis=0, keepdims=True)
        mx = rgb.max(axis=0, keepdims=True)
        rgb_norm = (rgb - mn) / np.maximum(mx - mn, 1e-6)
    else:
        rgb_norm = np.full((n_rows, 3), 0.5, dtype=np.float32)

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2],
               c=rgb_norm, s=18, alpha=0.85, depthshade=True)
    ax.set_title(f"ChunkInstance UMAP (nomic embeddings, n={n_rows})")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[UMAP] saved -> {os.path.abspath(output_path)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("Initializing database...")
    database.init_db()
    conn = database.get_connection()

    print("Starting Firefox...")
    profile_path = (
        r"C:\Users\isaac\AppData\Roaming\Mozilla\Firefox\Profiles\iwunpegz.ublock"
    )
    options = FirefoxOptions()
    options.add_argument("-profile")
    options.add_argument(profile_path)
    driver = webdriver.Firefox(options=options)

    url = "https://www.tarot.com/search?q=love&size=n_20_n"

    print("Loading Nomic v1 GGUF embedder (GPU)...")
    embedder = ChunkInstanceEmbedder()
    probe = embedder._embedder.embed_query("warmup")
    print(
        f"  model={embedder._embedder.model_name!r} "
        f"device={embedder._embedder.device!r} "
        f"dim={probe.shape[0]} "
        f"probe_norm={float(np.linalg.norm(probe)):.4f}"
    )

    try:
        print(f"\nScanning: {url}")
        result = run_pipeline_live(
            driver, url,
            max_duration=30, persist=True, conn=conn,
            single_pass=False,
            render_instances=True, embed_instances=True,
            detect_signal_fields=True,
            embedder=embedder,
        )

        summary = result.as_summary()
        print(
            f"\nSnapshot {summary['snapshot_id']} | "
            f"patterns={summary.get('content_pattern_count', 0)} | "
            f"chunks={summary.get('chunks', 0)} | "
            f"instances={summary.get('instances', 0)} | "
            f"unique_texts={summary.get('unique_instance_texts', 0)} | "
            f"cuML={USE_CUML} | "
            f"elapsed={summary.get('elapsed_ms', 0):.1f} ms"
        )

        # -------------------- Instrumentation --------------------
        print_pipeline_instrumentation(result)
        print_first_instance_per_chunk(result)

        if not result.chunks or not result.instances:
            print("No chunks / instances -- nothing to cluster.")
            return

        # -------------------- Build graphs from distilled trie --------------------
        T, G, root, xpath_to_id = build_content_graphs(result.content_tree)
        _print_heuristic_reasoning(T, G)

        # -------------------- Feature matrix --------------------
        X, names, kept = build_instance_feature_matrix(
            result, T, G, root, xpath_to_id,
        )
        print(f"\n[features] matrix shape={X.shape}  "
              f"instances_kept={len(kept)}/{len(result.instances)}")
        if X.shape[0] == 0:
            print("No mappable instances -- aborting clustering.")
            return
        print("  columns:", ", ".join(names))

        # -------------------- DBSCAN --------------------
        labels, eps, kdist = run_instance_dbscan(X, min_samples=4)

        plot_kdist(kdist, eps, "kdist_knee.png")
        plot_feature_variance(X, names, "feature_variance.png")
        plot_dbscan_pca(X, labels, eps, "dbscan_clusters.png")
        print(f"[plots] saved: kdist_knee.png, feature_variance.png, "
              f"dbscan_clusters.png")

        summarize_clusters(labels, kept, X, names)

        # -------------------- Global semantic UMAP --------------------
        umap_scatter_from_db(conn, output_path="umap_chunks.png")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
