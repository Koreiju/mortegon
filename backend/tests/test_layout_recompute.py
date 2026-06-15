"""Regression — LayoutService.recompute over the REAL GlobalTfidfStore.

The §16.5 live probe found that every real scan-end layout broadcast was
crashing: ``recompute`` treated the store's ``_chunk_meta`` (a LIST of
ChunkMeta dataclasses row-aligned with ``_chunk_ids``) as a dict keyed by
chunk_id (`'list' object has no attribute 'get'`), and the manual
``/api/recompute_umap`` route 500'd on a leftover ``n_comp`` local. This
pins the fixed contract: a workspace-scoped recompute over real store rows
produces a 6-vector LayoutFrame without touching an embedder.

Real store + real LayoutService; the store lives in a janitor-managed temp
dir (§R.9).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from backend.services.db_janitor import temp_db_dir
from backend.services.global_tfidf_store import ChunkMeta, GlobalTfidfStore
from backend.services.layout_service import LayoutService


@pytest.fixture()
def store_with_rows(monkeypatch):
    with temp_db_dir("tfidf_recompute") as tmp:
        store = GlobalTfidfStore(tmp)
        texts, metas = [], []
        for i in range(10):
            texts.append(
                f"university library catalogue volume {i} "
                f"with archive holdings and special collections {i}"
            )
            metas.append(ChunkMeta(
                chunk_id=f"inst_{i}",
                url=f"https://example.org/page{i % 2}",
                snapshot_id="s1",
            ))
        added = store.add_chunks(texts, metas)
        assert added == 10
        # Route the singleton accessor at this store so recompute's lazy
        # `get_default_store()` resolves to the temp-dir instance.
        import backend.services.global_tfidf_store as gts
        monkeypatch.setattr(gts, "_default_store", store)
        monkeypatch.setenv("WFH_TFIDF_DIR", tmp)
        yield store


def test_recompute_handles_list_shaped_chunk_meta(store_with_rows):
    layout = LayoutService(broadcast=None)
    # Workspace-scoped: scanner-emitted rows carry no workspace metadata —
    # they fall through into any scope (the default-workspace convention).
    frame = layout.recompute(min_docs=8, workspace_id="_default")
    assert frame is not None, "recompute returned no frame over 10 real rows"
    assert len(frame.coords) == 10
    for v in frame.coords.values():
        assert len(v) == 6  # §1.8 — xyz + HSV
    # URL grouping flowed from the row-aligned ChunkMeta (two URL roots).
    assert len(frame.url_roots) == 2


def test_recompute_unscoped_matches_scoped_for_scanner_rows(store_with_rows):
    layout = LayoutService(broadcast=None)
    scoped = layout.recompute(min_docs=8, workspace_id="_default")
    unscoped = layout.recompute(min_docs=8, workspace_id="")
    assert scoped is not None and unscoped is not None
    assert set(scoped.coords) == set(unscoped.coords)
