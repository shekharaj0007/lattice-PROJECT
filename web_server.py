"""Flask web server — deployable on Render."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from chat_assistant import chat_completion
from circularity_predictor import load_models, predict_at_point, predict_grid, train_and_save, find_best_position
from lattice_geometry_engine import LatticeConfig, TOOL_DIAMETER_OPTIONS, analyze_position
from report_builder import build_full_report
from synthetic_view import render_heatmap, render_lattice_view


def _load_dotenv() -> None:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
load_models()


@app.after_request
def no_cache_static(response):
    if not request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def _cfg_from_data(data: dict) -> LatticeConfig:
    return LatticeConfig(
        working_area_um=float(data["working_area"]),
        tool_diameter_um=float(data["tool_diameter"]),
        pore_diameter_um=float(data["pore_diameter"]),
    )


def _img_b64(png: bytes) -> str:
    return base64.b64encode(png).decode("ascii")


@app.route("/api/version")
def version_api():
    return jsonify({"ui_version": 5, "app": "LatticeFlow EDM", "port_hint": 5050})


@app.route("/api/tool-options")
def tool_options_api():
    return jsonify({"options": TOOL_DIAMETER_OPTIONS})


@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message required"}), 400
    result = chat_completion(
        user_message=message,
        history=data.get("history") or [],
        analysis_payload=data.get("analysis"),
        api_key=data.get("api_key"),
    )
    return jsonify(result)


@app.route("/")
def index():
    return render_template("index.html", tool_options=TOOL_DIAMETER_OPTIONS)


@app.route("/report")
def report_page():
    return render_template("report.html")


@app.route("/api/bounds", methods=["POST"])
def bounds():
    data = request.get_json(force=True) or {}
    try:
        cfg = _cfg_from_data(data)
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid geometry fields"}), 400
    lo, hi = cfg.position_bounds()
    return jsonify({
        "x_min": round(lo, 1), "x_max": round(hi, 1),
        "y_min": round(lo, 1), "y_max": round(hi, 1),
        "tool_radius": cfg.tool_radius,
        "tool_pore_ratio": round(cfg.tool_pore_ratio, 2),
        "unit_cell_um": round(cfg.unit_cell_um, 1),
        "hint": (
            f"Place tool center between {lo:.0f} and {hi:.0f} µm "
            f"(tool radius {cfg.tool_radius:.0f} µm inside {cfg.working_area_um:.0f} µm area)."
        ),
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True) or {}
    try:
        cfg = _cfg_from_data(data)
        I = float(data["peak_current"])
        T = float(data["pulse_on"])
        D = float(data["duty"])
        x = float(data["tool_x"])
        y = float(data["tool_y"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "All fields required with valid numbers"}), 400

    lo, hi = cfg.position_bounds()
    if not (lo <= x <= hi and lo <= y <= hi):
        return jsonify({"error": f"Position must be within [{lo:.0f}, {hi:.0f}] µm for this tool size"}), 400
    if I <= 0 or T <= 0 or D <= 0 or D > 100:
        return jsonify({"error": "Invalid EDM parameters"}), 400
    if cfg.pore_diameter_um <= 0 or cfg.working_area_um <= cfg.tool_diameter_um:
        return jsonify({"error": "Pore must be > 0 and working area must exceed tool diameter"}), 400

    result = predict_at_point(I, T, D, x, y, cfg)
    geom = analyze_position(cfg, x, y)
    optimal = find_best_position(I, T, D, cfg, x, y)
    report = build_full_report(
        cfg, geom, I, T, D, x, y,
        result["circularity_1to5"], result["supporting_material_ok"], result["pass_fail"],
        optimal_position=optimal,
    )
    lattice_png = render_lattice_view(x, y, I, T, D, cfg, result)

    return jsonify({
        "success": True,
        "results": result,
        "report": report,
        "lattice_image": _img_b64(lattice_png),
    })


@app.route("/api/grid-scan", methods=["POST"])
def grid_scan():
    data = request.get_json(force=True) or {}
    try:
        cfg = _cfg_from_data(data)
        I, T, D = float(data["peak_current"]), float(data["pulse_on"]), float(data["duty"])
        step = float(data.get("grid_step", 75))
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid parameters"}), 400

    grid = predict_grid(I, T, D, cfg, step_um=step)
    import numpy as np
    bi = int(np.argmax(grid["circularity"]))
    bp = grid["positions"][bi]
    br = predict_at_point(I, T, D, bp[0], bp[1], cfg)
    return jsonify({
        "success": True,
        "best_position": {"x": float(bp[0]), "y": float(bp[1])},
        "best_circularity": float(grid["circularity"][bi]),
        "best_result": br,
        "pass_count": int(np.sum((grid["circularity"] >= 3.5) & grid["supporting_ok"])),
        "total_points": len(grid["circularity"]),
        "heatmap_image": _img_b64(render_heatmap(grid["positions"], grid["circularity"], I, T, D, cfg)),
        "best_lattice_image": _img_b64(render_lattice_view(bp[0], bp[1], I, T, D, cfg, br)),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n  LatticeFlow EDM -> http://localhost:{port}")
    print("  UI version: 5 — look for 'UI v5' badge top-right")
    print("  Wrong page? You may have old tab on :5000 or Streamlit on :8501\n")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
