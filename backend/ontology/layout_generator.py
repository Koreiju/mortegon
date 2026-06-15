import numpy as np
from typing import List, Dict, Any


class LayoutGenerator:
    """Deterministic radial-tree layout: hash-direction sphere root + radial rings.

    Scanner-internal DOM-snapshot tree layout (NOT the chunk-projector layout
    authority — that is the UMAP-linear-radial `LayoutService`, §6.1). The
    forbidden golden-angle Fibonacci-sphere distribution (§K.1) is replaced
    here by the §6.1-permitted **hash-direction** unit-vector placement: a
    deterministic per-index hash assigns each root child a direction on the
    unit sphere, scaled to an equal radius. Per-parent fan-rings (below) are
    local tree-edge layout, not global concentric shells.

    Algorithm:
      - Root at origin (0,0,0), never emitted as a visible node.
      - Root's children are placed on a sphere (equal radius) whose radius
        auto-scales so that neighbouring nodes are spaced ≥ 2× their diameter;
        directions are deterministic hash-of-index unit vectors (§6.1).
      - For every deeper node with N children:
          * N=1 → push the child directly outward along the parent's
            radial direction by EDGE_LENGTH.
          * N>1 → place children on a ring perpendicular to the parent's
            radial direction.  The ring radius is sized so the arc gap
            between adjacent children ≈ 2× node diameter.  The ring centre
            sits at parent + axial_offset × direction, with axial_offset
            chosen so that the Euclidean parent→child distance equals
            the effective edge length.
      - Every parent→child edge has equal Euclidean length (auto-scaled
        upward when fan-out demands a wide ring).
      - Shadow DOM children (node['shadowRoot']['children']) are merged
        with light DOM children for layout purposes.
    """

    # Frontend node sphere radius (SphereGeometry in projector.js)
    NODE_RADIUS = 0.6
    NODE_DIAMETER = NODE_RADIUS * 2        # 1.2
    MIN_SPACING = NODE_DIAMETER * 2        # 2.4  (arc gap ≈ 2× diameter)
    BASE_EDGE_LENGTH = 8.0                 # Default parent-child edge length

    # ------------------------------------------------------------------
    # Hash-direction unit-sphere placement (§6.1 — replaces the forbidden
    # golden-angle Fibonacci sphere, §K.1). Deterministic per-index so
    # retries reproduce positions; equal radius after scaling.
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_sphere_directions(num_pts: int) -> np.ndarray:
        """Return *num_pts* deterministic unit-sphere directions via a stable
        per-index hash (§6.1 hash-direction form — NOT golden-angle)."""
        if num_pts == 0:
            return np.empty((0, 3))
        if num_pts == 1:
            return np.array([[0.0, 0.0, 1.0]])

        import hashlib
        out = np.empty((num_pts, 3), dtype=float)
        for i in range(num_pts):
            # Stable hash (md5) so directions are reproducible across runs
            # regardless of PYTHONHASHSEED (the builtin hash() is salted).
            digest = hashlib.md5(f"{i}:{num_pts}".encode()).digest()
            ax = (digest[0] / 255.0) * 2 - 1
            ay = (digest[1] / 255.0) * 2 - 1
            az = (digest[2] / 255.0) * 2 - 1
            v = np.array([ax, ay, az], dtype=float)
            n = float(np.linalg.norm(v))
            if n < 1e-9:
                v, n = np.array([0.0, 0.0, 1.0]), 1.0
            out[i] = v / n
        return out

    # ------------------------------------------------------------------
    # Orthonormal basis perpendicular to a direction
    # ------------------------------------------------------------------

    @staticmethod
    def _orthonormal_basis(direction: np.ndarray):
        """Return two unit vectors (u, v) perpendicular to *direction*."""
        d = direction / np.linalg.norm(direction)
        # Pick an arbitrary axis that is NOT parallel to d
        arbitrary = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 \
            else np.array([0.0, 1.0, 0.0])
        u = np.cross(d, arbitrary)
        u /= np.linalg.norm(u)
        v = np.cross(d, u)
        return u, v

    # ------------------------------------------------------------------
    # Collect all children (light DOM + shadow DOM)
    # ------------------------------------------------------------------

    @staticmethod
    def _all_children(node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return light DOM children + shadow DOM children merged."""
        children = list(node.get('children', []))
        shadow = node.get('shadowRoot')
        if shadow and isinstance(shadow, dict):
            children.extend(shadow.get('children', []))
        return children

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @classmethod
    def apply_radial_tree_layout(cls, tree_struct: Dict[str, Any]) -> Dict[str, Any]:
        """Assign deterministic 3-D coordinates to every node in *tree_struct*.

        Mutates the tree in-place, adding ``layout_x``, ``layout_y``,
        ``layout_z`` and ``depth`` keys to every node dict.

        Traverses both light DOM children and shadow DOM children.
        """
        # Root at origin
        tree_struct['layout_x'] = 0.0
        tree_struct['layout_y'] = 0.0
        tree_struct['layout_z'] = 0.0
        tree_struct['depth'] = 0

        children = cls._all_children(tree_struct)
        N = len(children)
        if N == 0:
            return tree_struct

        # -----------------------------------------------------------
        # Root children: hash-direction unit sphere (§6.1), equal radius.
        # Radius auto-sized so nearest-neighbour arc ≥ MIN_SPACING using
        # the same R ≥ MIN_SPACING × √(N / (4π)) sphere-packing estimate.
        # -----------------------------------------------------------
        root_radius = max(
            cls.BASE_EDGE_LENGTH,
            cls.MIN_SPACING * np.sqrt(N / (4 * np.pi)),
        )

        pts = cls._generate_sphere_directions(N)
        pts *= root_radius

        for i, child in enumerate(children):
            child['layout_x'] = float(pts[i][0])
            child['layout_y'] = float(pts[i][1])
            child['layout_z'] = float(pts[i][2])
            child['depth'] = 1
            cls._layout_subtree(child, depth=1)

        return tree_struct

    # ------------------------------------------------------------------
    # Recursive radial-ring placement for deeper children
    # ------------------------------------------------------------------

    @classmethod
    def _layout_subtree(cls, node: Dict[str, Any], depth: int) -> None:
        """Recursively place children of *node* in radial rings.

        Traverses both light DOM children and shadow DOM children.
        """
        children = cls._all_children(node)
        N = len(children)
        if N == 0:
            return

        pos = np.array([node['layout_x'], node['layout_y'], node['layout_z']])
        norm = np.linalg.norm(pos)

        # Radial direction = outward from origin through parent
        direction = pos / norm if norm > 1e-6 else np.array([0.0, 0.0, 1.0])

        if N == 1:
            # Single child: push directly outward along parent direction
            child_pos = pos + cls.BASE_EDGE_LENGTH * direction
            children[0]['layout_x'] = float(child_pos[0])
            children[0]['layout_y'] = float(child_pos[1])
            children[0]['layout_z'] = float(child_pos[2])
            children[0]['depth'] = depth + 1
            cls._layout_subtree(children[0], depth + 1)
        else:
            # Multiple children: ring perpendicular to radial direction.
            # Ring radius so chord distance between adjacent children ≥ MIN_SPACING:
            #   chord = 2r·sin(π/N) ≥ MIN_SPACING  →  r ≥ MIN_SPACING / (2·sin(π/N))
            ring_radius = cls.MIN_SPACING / (2 * np.sin(np.pi / N))

            # Effective edge length must be ≥ ring_radius so that the
            # axial offset h = √(edge² − ring²) remains positive.
            edge_len = max(cls.BASE_EDGE_LENGTH, ring_radius + 0.5)
            h = np.sqrt(edge_len**2 - ring_radius**2)

            # Ring centre sits h units outward from parent
            center = pos + h * direction

            # Orthonormal basis for the ring plane
            u, v = cls._orthonormal_basis(direction)

            for i, child in enumerate(children):
                angle = 2.0 * np.pi * i / N
                child_pos = center + ring_radius * (
                    np.cos(angle) * u + np.sin(angle) * v
                )
                child['layout_x'] = float(child_pos[0])
                child['layout_y'] = float(child_pos[1])
                child['layout_z'] = float(child_pos[2])
                child['depth'] = depth + 1
                cls._layout_subtree(child, depth + 1)

    # ------------------------------------------------------------------
    # Bounding radius
    # ------------------------------------------------------------------

    @staticmethod
    def compute_bounding_radius(tree_struct: Dict[str, Any]) -> float:
        """Walk the tree and return the maximum distance from the origin."""
        max_r = 0.0
        stack = [tree_struct]
        while stack:
            node = stack.pop()
            x = node.get('layout_x', 0.0)
            y = node.get('layout_y', 0.0)
            z = node.get('layout_z', 0.0)
            r = (x * x + y * y + z * z) ** 0.5
            if r > max_r:
                max_r = r
            stack.extend(node.get('children', []))
            shadow = node.get('shadowRoot')
            if shadow:
                stack.extend(shadow.get('children', []))
        return max_r
