"""Synthetic lattice + tool visualization."""

from __future__ import annotations

import io
import matplotlib
matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from lattice_geometry_engine import (
    LatticeConfig, node_centers, pore_centers, strut_segments, analyze_position,
)


def render_lattice_view(
    tool_x: float, tool_y: float,
    peak_current: float, pulse_on: float, duty: float,
    cfg: LatticeConfig,
    pred: dict | None = None,
) -> bytes:
    w = cfg.working_area_um
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), dpi=120)
    ax.set_xlim(-w * 0.03, w * 1.03)
    ax.set_ylim(-w * 0.03, w * 1.03)
    ax.set_aspect("equal")
    ax.set_facecolor("#f8f6f1")

    uc = cfg.unit_cell_um
    for i in range(cfg.n_cells + 1):
        ax.axhline(i * uc, color="#aaa", lw=0.4, alpha=0.5)
        ax.axvline(i * uc, color="#aaa", lw=0.4, alpha=0.5)

    for x1, y1, x2, y2 in strut_segments(cfg):
        ax.plot([x1, x2], [y1, y2], color="#1a1a1a", lw=2.5, solid_capstyle="round")

    for px, py in pore_centers(cfg):
        ax.add_patch(Circle((px, py), cfg.pore_radius, fc="white", ec="#888", lw=1.2))

    for nx, ny in node_centers(cfg):
        ax.add_patch(Circle((nx, ny), cfg.node_radius, fc="#c44", ec="#800", lw=1.2, alpha=0.85))

    ax.add_patch(Circle((tool_x, tool_y), cfg.tool_radius, fc="none", ec="#5b21b6", lw=2.5, ls="--"))
    ax.plot(tool_x, tool_y, "k+", ms=10, mew=2)

    machined_r = cfg.tool_radius * 0.88
    ax.add_patch(Circle((tool_x, tool_y), machined_r, fc="none", ec="#dc2626", lw=2))

    ax.plot(0, 0, "ko", ms=5)
    ax.annotate("(0,0)", (0, 0), xytext=(6, 6), textcoords="offset points", fontsize=8)

    title = f"Tool Ø{cfg.tool_diameter_um:.0f}µm @ ({tool_x:.0f},{tool_y:.0f})  |  {peak_current}A {pulse_on}µs {duty}%"
    if pred:
        title += f"\nCirc: {pred['circularity_1to5']}/5  |  {pred['pass_fail']}"
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("x (µm)")
    ax.set_ylabel("y (µm)")

    sb = min(500, w * 0.33)
    ax.plot([w * 0.05, w * 0.05 + sb], [w * 0.04, w * 0.04], "k-", lw=2)
    ax.text(w * 0.05 + sb / 2, w * 0.07, f"{sb:.0f} µm", ha="center", fontsize=8)
    ax.text(
        w * 0.03, w * 0.97,
        f"White = pore (Ø{cfg.pore_diameter_um:.0f}µm)  |  Red = node (fixed Ø{cfg.node_radius * 2:.0f}µm)",
        fontsize=7, va="top", color="#555",
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_heatmap(positions, circularity, peak_current, pulse_on, duty, cfg: LatticeConfig) -> bytes:
    xs, ys = np.unique(positions[:, 0]), np.unique(positions[:, 1])
    grid = circularity.reshape(len(ys), len(xs))
    fig, ax = plt.subplots(figsize=(9, 7), dpi=120)
    im = ax.imshow(grid, origin="lower", extent=[xs[0], xs[-1], ys[0], ys[-1]],
                   aspect="equal", cmap="RdYlGn", vmin=1, vmax=5)
    plt.colorbar(im, ax=ax, label="Circularity (1–5)")
    ax.set_title(f"Heatmap — {cfg.working_area_um:.0f}µm area, tool Ø{cfg.tool_diameter_um:.0f}µm")
    uc = cfg.unit_cell_um
    for i in range(cfg.n_cells + 1):
        ax.axhline(i * uc, color="white", lw=0.4, alpha=0.6)
        ax.axvline(i * uc, color="white", lw=0.4, alpha=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
