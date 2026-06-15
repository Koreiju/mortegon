import pytest
import numpy as np
from backend.ontology.layout_generator import LayoutGenerator

def test_root_layout():
    tree = {"xpath": "/", "children": []}
    LayoutGenerator.apply_radial_tree_layout(tree)

    assert tree["layout_x"] == 0.0
    assert tree["layout_y"] == 0.0
    assert tree["layout_z"] == 0.0

def test_depth_1_equal_radius_layout():
    children = [{"xpath": f"/child_{i}", "children": []} for i in range(10)]
    tree = {"xpath": "/", "children": children}

    LayoutGenerator.apply_radial_tree_layout(tree)

    # All children should be on a sphere of equal radius (hash-direction sphere, §6.1)
    distances = []
    for c in tree["children"]:
        d = np.sqrt(c["layout_x"]**2 + c["layout_y"]**2 + c["layout_z"]**2)
        distances.append(d)

    # All at the same radius
    assert all(np.isclose(d, distances[0]) for d in distances)

    # Radius should be at least BASE_EDGE_LENGTH
    assert distances[0] >= LayoutGenerator.BASE_EDGE_LENGTH - 1e-6

def test_single_child_pushed_outward():
    """A single child should be placed directly outward along parent direction."""
    tree = {
        "xpath": "/",
        "children": [{
            "xpath": "/child_0",
            "children": [{
                "xpath": "/child_0/grandchild_0",
                "children": []
            }]
        }]
    }

    LayoutGenerator.apply_radial_tree_layout(tree)

    parent = tree["children"][0]
    child = parent["children"][0]

    parent_pos = np.array([parent["layout_x"], parent["layout_y"], parent["layout_z"]])
    child_pos = np.array([child["layout_x"], child["layout_y"], child["layout_z"]])

    # Child should be further from origin than parent
    assert np.linalg.norm(child_pos) > np.linalg.norm(parent_pos)

    # Edge length should be BASE_EDGE_LENGTH
    edge = np.linalg.norm(child_pos - parent_pos)
    assert np.isclose(edge, LayoutGenerator.BASE_EDGE_LENGTH)

def test_ring_spacing():
    """Multiple children should be placed in a ring with arc spacing >= MIN_SPACING."""
    sub_children = [{"xpath": f"/child_0/sub_{i}", "children": []} for i in range(5)]
    tree = {
        "xpath": "/",
        "children": [{
            "xpath": "/child_0",
            "children": sub_children
        }]
    }

    LayoutGenerator.apply_radial_tree_layout(tree)

    parent = tree["children"][0]
    positions = []
    for sc in parent["children"]:
        positions.append(np.array([sc["layout_x"], sc["layout_y"], sc["layout_z"]]))

    # Check that all children are equidistant from parent
    parent_pos = np.array([parent["layout_x"], parent["layout_y"], parent["layout_z"]])
    edges = [np.linalg.norm(p - parent_pos) for p in positions]
    assert all(np.isclose(e, edges[0], atol=1e-6) for e in edges)

    # Check minimum spacing between adjacent ring nodes
    N = len(positions)
    for i in range(N):
        j = (i + 1) % N
        gap = np.linalg.norm(positions[i] - positions[j])
        # Arc gap should be approximately >= MIN_SPACING
        assert gap >= LayoutGenerator.MIN_SPACING * 0.95

def test_bounding_radius():
    children = [{"xpath": f"/child_{i}", "children": []} for i in range(20)]
    tree = {"xpath": "/", "children": children}
    LayoutGenerator.apply_radial_tree_layout(tree)

    br = LayoutGenerator.compute_bounding_radius(tree)
    assert br > 0

def test_shadow_root_children_get_layout():
    """Shadow DOM children should receive layout coordinates just like light DOM children."""
    tree = {
        "xpath": "/",
        "children": [
            {"xpath": "/light_child", "children": []}
        ],
        "shadowRoot": {
            "mode": "open",
            "children": [
                {"xpath": "/shadow_child_0", "children": []},
                {"xpath": "/shadow_child_1", "children": []},
            ]
        }
    }

    LayoutGenerator.apply_radial_tree_layout(tree)

    # All 3 children (1 light + 2 shadow) should have layout coordinates
    light = tree["children"][0]
    shadow0 = tree["shadowRoot"]["children"][0]
    shadow1 = tree["shadowRoot"]["children"][1]

    for node in [light, shadow0, shadow1]:
        assert "layout_x" in node
        assert "layout_y" in node
        assert "layout_z" in node
        assert node["depth"] == 1
        dist = np.sqrt(node["layout_x"]**2 + node["layout_y"]**2 + node["layout_z"]**2)
        assert dist > 0  # Not at origin

    # All should be on the same sphere radius (hash-direction placement, §6.1)
    d_light = np.sqrt(light["layout_x"]**2 + light["layout_y"]**2 + light["layout_z"]**2)
    d_shadow0 = np.sqrt(shadow0["layout_x"]**2 + shadow0["layout_y"]**2 + shadow0["layout_z"]**2)
    d_shadow1 = np.sqrt(shadow1["layout_x"]**2 + shadow1["layout_y"]**2 + shadow1["layout_z"]**2)
    assert np.isclose(d_light, d_shadow0)
    assert np.isclose(d_light, d_shadow1)

def test_nested_shadow_root_layout():
    """Shadow DOM children at deeper levels should also get positioned."""
    tree = {
        "xpath": "/",
        "children": [{
            "xpath": "/host",
            "children": [],
            "shadowRoot": {
                "mode": "open",
                "children": [
                    {"xpath": "/host/shadow_a", "children": []},
                    {"xpath": "/host/shadow_b", "children": []},
                ]
            }
        }]
    }

    LayoutGenerator.apply_radial_tree_layout(tree)

    host = tree["children"][0]
    shadow_a = host["shadowRoot"]["children"][0]
    shadow_b = host["shadowRoot"]["children"][1]

    # Host at depth 1
    assert host["depth"] == 1
    # Shadow children at depth 2
    assert shadow_a["depth"] == 2
    assert shadow_b["depth"] == 2

    # Shadow children should be further from origin than host
    host_dist = np.linalg.norm([host["layout_x"], host["layout_y"], host["layout_z"]])
    sa_dist = np.linalg.norm([shadow_a["layout_x"], shadow_a["layout_y"], shadow_a["layout_z"]])
    sb_dist = np.linalg.norm([shadow_b["layout_x"], shadow_b["layout_y"], shadow_b["layout_z"]])
    assert sa_dist > host_dist
    assert sb_dist > host_dist
