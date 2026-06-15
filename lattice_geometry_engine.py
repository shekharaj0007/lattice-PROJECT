"""
Lattice geometry engine — dynamic working area, tool, and pore sizes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

TOOL_DIAMETER_OPTIONS = list(range(400, 1600, 100))  # 400–1500 µm
# Physical node size from lab lattice geometry (fixed; does not change with user pore input)
DEFAULT_NODE_DIAMETER_UM = 235.6


@dataclass
class LatticeConfig:
    working_area_um: float = 1500.0
    tool_diameter_um: float = 900.0
    pore_diameter_um: float = 235.6
    unit_cell_um: float | None = None  # auto = working_area / 3

    def __post_init__(self):
        if self.unit_cell_um is None:
            self.unit_cell_um = self.working_area_um / 3.0
        self.tool_radius = self.tool_diameter_um / 2.0
        self.pore_radius = self.pore_diameter_um / 2.0
        # Nodes are fixed physical strut junctions; only pore (white) scales with user input
        self.node_radius = DEFAULT_NODE_DIAMETER_UM / 2.0
        self.n_cells = max(1, int(round(self.working_area_um / self.unit_cell_um)))

    @property
    def tool_pore_ratio(self) -> float:
        return self.tool_diameter_um / max(self.pore_diameter_um, 1e-6)

    def position_bounds(self) -> tuple[float, float]:
        """Valid tool center range so full circle stays inside working area."""
        m = self.tool_radius
        return m, self.working_area_um - m


@dataclass
class GeometryFeatures:
    tool_x: float
    tool_y: float
    min_dist_to_strut: float
    min_dist_to_node_center: float
    nodes_inside_tool: int
    pores_center_inside_tool: int
    strut_intersection_length: float
    pore_overlap_fraction: float
    node_overlap_fraction: float
    geometry_risk: float
    tool_pore_ratio: float


def _node_grid_size(cfg: LatticeConfig) -> int:
    return cfg.n_cells + 1


def node_centers(cfg: LatticeConfig) -> list[tuple[float, float]]:
    n = _node_grid_size(cfg)
    uc = cfg.unit_cell_um
    return [(i * uc, j * uc) for i in range(n) for j in range(n)]


def pore_centers(cfg: LatticeConfig) -> list[tuple[float, float]]:
    uc = cfg.unit_cell_um
    pts = []
    for i in range(cfg.n_cells):
        for j in range(cfg.n_cells):
            pts.append((i * uc + uc / 2, j * uc + uc / 2))
    return pts


def strut_segments(cfg: LatticeConfig) -> list[tuple[float, float, float, float]]:
    segs = []
    n = _node_grid_size(cfg)
    w = cfg.working_area_um
    uc = cfg.unit_cell_um
    for k in range(n):
        y = k * uc
        if y <= w:
            segs.append((0, y, w, y))
        x = k * uc
        if x <= w:
            segs.append((x, 0, x, w))
    return segs


def _dist_point_to_segment(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def circle_segment_intersection_length(cx, cy, r, x1, y1, x2, y2, n=40) -> float:
    length = 0.0
    prev_inside = None
    prev_pt = None
    for t in np.linspace(0, 1, n):
        px = x1 + t * (x2 - x1)
        py = y1 + t * (y2 - y1)
        inside = math.hypot(px - cx, py - cy) <= r
        if prev_inside and inside and prev_pt:
            length += math.hypot(px - prev_pt[0], py - prev_pt[1])
        prev_inside = inside
        prev_pt = (px, py)
    return length


def pore_circle_overlap(cx, cy, tool_r, pore_x, pore_y, pore_r) -> float:
    d = math.hypot(cx - pore_x, cy - pore_y)
    if d >= tool_r + pore_r:
        return 0.0
    if d <= abs(tool_r - pore_r):
        return min(1.0, (tool_r / max(pore_r, 1e-6)) ** 2 * 0.5)
    r1, r2 = tool_r, pore_r
    if d < 1e-9:
        return 1.0
    part1 = r1 * r1 * math.acos(min(1, max(-1, (d * d + r1 * r1 - r2 * r2) / (2 * d * r1))))
    part2 = r2 * r2 * math.acos(min(1, max(-1, (d * d + r2 * r2 - r1 * r1) / (2 * d * r2))))
    part3 = 0.5 * math.sqrt(max(0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)))
    return min(1.0, (part1 + part2 - part3) / (math.pi * pore_r * pore_r))


def analyze_position(cfg: LatticeConfig, tool_x: float, tool_y: float) -> GeometryFeatures:
    cx, cy, r = tool_x, tool_y, cfg.tool_radius
    nodes = node_centers(cfg)
    pores = pore_centers(cfg)
    segs = strut_segments(cfg)

    min_node = min(math.hypot(cx - nx, cy - ny) for nx, ny in nodes)
    min_strut = min(_dist_point_to_segment(cx, cy, *s) for s in segs) if segs else 0

    nodes_in = sum(1 for nx, ny in nodes if math.hypot(cx - nx, cy - ny) <= r + cfg.node_radius)
    pores_in = sum(1 for px, py in pores if math.hypot(cx - px, cy - py) <= r)

    strut_len = sum(circle_segment_intersection_length(cx, cy, r, *s) for s in segs)
    pore_frac = max((pore_circle_overlap(cx, cy, r, px, py, cfg.pore_radius) for px, py in pores), default=0)
    node_frac = sum(pore_circle_overlap(cx, cy, r, nx, ny, cfg.node_radius) for nx, ny in nodes) / max(len(nodes), 1)

    scale = cfg.unit_cell_um / 500.0
    strut_risk = max(0, 1 - min_strut / (200.0 * scale))
    intersect_risk = min(1.0, strut_len / (800.0 * scale))
    ratio_factor = min(1.0, max(0, (cfg.tool_pore_ratio - 2.0) / 4.0))
    geometry_risk = min(1.0, 0.5 * strut_risk + 0.3 * intersect_risk + 0.2 * ratio_factor)

    return GeometryFeatures(
        tool_x=tool_x, tool_y=tool_y,
        min_dist_to_strut=min_strut, min_dist_to_node_center=min_node,
        nodes_inside_tool=nodes_in, pores_center_inside_tool=pores_in,
        strut_intersection_length=strut_len,
        pore_overlap_fraction=pore_frac, node_overlap_fraction=node_frac,
        geometry_risk=geometry_risk, tool_pore_ratio=cfg.tool_pore_ratio,
    )


def feature_vector(cfg: LatticeConfig, tool_x: float, tool_y: float) -> np.ndarray:
    g = analyze_position(cfg, tool_x, tool_y)
    lo, hi = cfg.position_bounds()
    return np.array([
        tool_x / cfg.working_area_um, tool_y / cfg.working_area_um,
        g.min_dist_to_strut, g.min_dist_to_node_center,
        g.nodes_inside_tool, g.pores_center_inside_tool,
        g.strut_intersection_length, g.pore_overlap_fraction,
        g.node_overlap_fraction, g.geometry_risk,
        cfg.tool_pore_ratio, cfg.working_area_um, cfg.tool_diameter_um,
    ])


def grid_positions(cfg: LatticeConfig, step_um: float = 75.0) -> np.ndarray:
    lo, hi = cfg.position_bounds()
    if hi <= lo:
        return np.array([[cfg.working_area_um / 2, cfg.working_area_um / 2]])
    xs = np.arange(lo, hi + 1, step_um)
    ys = np.arange(lo, hi + 1, step_um)
    return np.array([[x, y] for x in xs for y in ys])
