"""Tests for cross-page loop closure pattern registry."""
import pytest
from backend.analytics.loop_closure import PatternRegistry


@pytest.fixture
def registry():
    return PatternRegistry()


def test_register_single_snapshot(registry):
    hashes = {"/html": 100, "/html/body": 200, "/html/body/div": 300}
    count = registry.register_snapshot(
        url="https://a.com", snapshot_id="s1",
        node_hashes=hashes, subtree_sizes={"/html": 10, "/html/body": 8, "/html/body/div": 5}
    )
    assert count == 0  # No cross-page matches yet


def test_cross_page_detection(registry):
    hashes1 = {"/html/body/nav": 500, "/html/body/main": 600}
    hashes2 = {"/html/body/nav": 500, "/html/body/content": 700}

    registry.register_snapshot(
        url="https://a.com", snapshot_id="s1", node_hashes=hashes1,
        subtree_sizes={"/html/body/nav": 5, "/html/body/main": 10}
    )
    cross = registry.register_snapshot(
        url="https://b.com", snapshot_id="s2", node_hashes=hashes2,
        subtree_sizes={"/html/body/nav": 5, "/html/body/content": 8}
    )
    # Hash 500 appears on both URLs
    assert cross >= 1


def test_find_cross_page_matches(registry):
    registry.register_snapshot(
        url="https://a.com", snapshot_id="s1",
        node_hashes={"/nav": 100, "/main": 200},
        subtree_sizes={"/nav": 5, "/main": 10}
    )
    registry.register_snapshot(
        url="https://b.com", snapshot_id="s2",
        node_hashes={"/nav": 100, "/sidebar": 300},
        subtree_sizes={"/nav": 5, "/sidebar": 4}
    )

    matches = registry.find_cross_page_matches(min_subtree_size=3)
    assert len(matches) >= 1
    assert matches[0]["wl_hash"] == 100
    assert len(matches[0]["urls"]) == 2


def test_min_subtree_size_filter(registry):
    registry.register_snapshot(
        url="https://a.com", snapshot_id="s1",
        node_hashes={"/tiny": 999},
        subtree_sizes={"/tiny": 1}  # Too small
    )
    registry.register_snapshot(
        url="https://b.com", snapshot_id="s2",
        node_hashes={"/tiny": 999},
        subtree_sizes={"/tiny": 1}
    )

    matches = registry.find_cross_page_matches(min_subtree_size=3)
    assert len(matches) == 0  # Filtered out by size


def test_get_cross_edges(registry):
    registry.register_snapshot(
        url="https://a.com", snapshot_id="s1",
        node_hashes={"/header": 42},
        subtree_sizes={"/header": 8}
    )
    registry.register_snapshot(
        url="https://b.com", snapshot_id="s2",
        node_hashes={"/header": 42},
        subtree_sizes={"/header": 7}
    )

    edges = registry.get_cross_edges(min_subtree_size=3)
    assert len(edges) == 1
    src, tgt = edges[0]
    assert src["url"] != tgt["url"]


def test_pattern_stats(registry):
    registry.register_snapshot(
        url="https://a.com", snapshot_id="s1",
        node_hashes={"/a": 1, "/b": 2, "/c": 3},
        subtree_sizes={"/a": 5, "/b": 5, "/c": 5}
    )
    registry.register_snapshot(
        url="https://b.com", snapshot_id="s2",
        node_hashes={"/x": 1, "/y": 4},
        subtree_sizes={"/x": 5, "/y": 5}
    )

    stats = registry.get_pattern_stats()
    assert stats["urls_registered"] == 2
    assert stats["total_patterns"] == 4
    assert stats["cross_page_patterns"] >= 1


def test_same_url_no_cross_match(registry):
    """Patterns on the same URL should not count as cross-page matches."""
    registry.register_snapshot(
        url="https://a.com", snapshot_id="s1",
        node_hashes={"/a": 1},
        subtree_sizes={"/a": 5}
    )
    registry.register_snapshot(
        url="https://a.com", snapshot_id="s2",
        node_hashes={"/b": 1},
        subtree_sizes={"/b": 5}
    )

    matches = registry.find_cross_page_matches(min_subtree_size=3)
    assert len(matches) == 0
