"""
backend.dom — ShadowDOM-coupled parsing, mining, and distillation.

Tier 2 of the three-tier architecture:
  Tier 1: backend.analytics.algorithms  (pure abstract algorithms)
  Tier 2: backend.dom                   (ShadowDOM-aware processing)
  Tier 3: backend.mapper                (orchestrator)

Modules:
  shadow_html_parser  — ShadowNode/ShadowDOM tree + HTML parser
  scanner             — Selenium-based DOM extraction with merge-tree dedup
  web_distiller_freq  — Spectral partitioning, content coagulation
  dom_wl_miner        — WL coloring engine + template grouping
  buta_extractor      — Bottom-up tree automaton for O(N) template extraction
  tfidf_cheeger_miner — TF-IDF + Cheeger cut spectral clustering
  content_tagger      — Content classification
  content_distiller_simple — Lightweight content filtering
  xpath_tree_builder  — XPath-based tree construction
"""
