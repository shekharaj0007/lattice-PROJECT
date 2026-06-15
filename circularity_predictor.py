"""ML + geometry heuristic circularity predictor (dynamic lattice config)."""

from __future__ import annotations

import csv
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from lattice_geometry_engine import LatticeConfig, analyze_position, feature_vector, grid_positions

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "outputs" / "circularity_grid_model.joblib"

DEFAULT_CFG = LatticeConfig(working_area_um=1500, tool_diameter_um=900, pore_diameter_um=235.6)


def _edm_features(I, T, D):
    return np.array([
        I, T, D,
        I * T * (D / 100.0),
        T * (100.0 - D) / max(D, 1e-6),
        I * D, T / (D + 1e-6),
    ])


def build_feature_row(cfg: LatticeConfig, I, T, D, x, y) -> np.ndarray:
    return np.concatenate([_edm_features(I, T, D), feature_vector(cfg, x, y)])


def _heuristic_circularity(cfg, g, I, T, D) -> float:
    base = 2.5
    if I <= 5 and T >= 130 and D >= 75:
        base = 4.2
    elif I <= 4.5 and T >= 140:
        base = 4.5
    if I >= 8:
        base = 1.8
    elif I >= 6 and T <= 75:
        base = 2.2
    if cfg.tool_pore_ratio > 4:
        base -= 0.8
    circ = base - 2.2 * g.geometry_risk
    if g.min_dist_to_strut > 150:
        circ += 0.3
    return float(np.clip(circ, 1, 5))


def _heuristic_supporting(cfg, g, I, T, D) -> bool:
    edm_gentle = I <= 5.5 and T >= 120 and D >= 72
    geom_ok = g.geometry_risk <= 0.55 and g.strut_intersection_length < 500 * (cfg.unit_cell_um / 500)
    if I >= 8:
        return False
    return edm_gentle and geom_ok or (edm_gentle and g.geometry_risk <= 0.45)


def load_training_data(cfg: LatticeConfig = DEFAULT_CFG):
    runs, labels = [], {}
    with open(ROOT / "data" / "original_16_runs.csv") as f:
        for r in csv.DictReader(f):
            runs.append({k: float(r[k]) if k != "Run" else int(r[k]) for k in r})
    with open(ROOT / "data" / "run_visual_labels.csv") as f:
        for r in csv.DictReader(f):
            labels[int(r["Run"])] = {
                "circularity": int(r["Boundary_circularity_1to5"]),
                "supporting_ok": int(r["Supporting_boundary_intact"]),
            }

    positions = grid_positions(cfg, step_um=150)
    X_list, y_circ, y_sup = [], [], []
    for run in runs:
        rid = int(run["Run"])
        lb = labels[rid]
        I, T, D = run["Peak_Current_A"], run["Pulse_On_Time_us"], run["Duty_Factor_pct"]
        for pos in positions:
            x, y = pos[0], pos[1]
            g = analyze_position(cfg, x, y)
            geom_penalty = 2.5 * g.geometry_risk
            edm_bonus = 0.5 if I <= 5 and T >= 130 and D >= 75 else (-1.0 if I >= 8 else 0)
            circ = np.clip(lb["circularity"] - geom_penalty + edm_bonus, 1, 5)
            sup = 1.0 if lb["supporting_ok"] and g.geometry_risk < 0.6 and I < 8 else 0.0
            if I <= 4.5 and T >= 140 and D >= 78:
                sup = max(sup, 1.0 - g.geometry_risk)
            X_list.append(build_feature_row(cfg, I, T, D, x, y))
            y_circ.append(circ)
            y_sup.append(sup)
    return np.array(X_list), np.array(y_circ), np.array(y_sup)


def train_and_save():
    X, y_circ, y_sup = load_training_data()
    mc = GradientBoostingRegressor(n_estimators=120, max_depth=4, random_state=42)
    ms = GradientBoostingRegressor(n_estimators=80, max_depth=3, random_state=42)
    mc.fit(X, y_circ)
    ms.fit(X, y_sup)
    bundle = {"circularity": mc, "supporting": ms, "n_features": X.shape[1]}
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    return bundle


def load_models():
    if not MODEL_PATH.exists():
        return train_and_save()
    m = joblib.load(MODEL_PATH)
    if m.get("n_features") != 20:
        return train_and_save()
    return m


def predict_at_point(
    peak_current: float, pulse_on: float, duty: float,
    tool_x: float, tool_y: float,
    cfg: LatticeConfig | None = None,
) -> dict:
    cfg = cfg or DEFAULT_CFG
    g = analyze_position(cfg, tool_x, tool_y)
    models = load_models()
    X = build_feature_row(cfg, peak_current, pulse_on, duty, tool_x, tool_y).reshape(1, -1)

    h_circ = _heuristic_circularity(cfg, g, peak_current, pulse_on, duty)
    h_sup = _heuristic_supporting(cfg, g, peak_current, pulse_on, duty)

    try:
        ml_circ = float(np.clip(models["circularity"].predict(X)[0], 1, 5))
        ml_sup = float(models["supporting"].predict(X)[0]) >= 0.5
    except Exception:
        ml_circ, ml_sup = h_circ, h_sup

    # Blend: weight heuristic more when config differs from training default
    drift = abs(cfg.tool_diameter_um - 900) / 900 + abs(cfg.pore_diameter_um - 235.6) / 235.6
    w = min(0.7, 0.35 + 0.15 * drift)
    circ = (1 - w) * ml_circ + w * h_circ
    circ = float(np.clip(circ, 1, 5))
    supporting_ok = h_sup if w > 0.5 else (ml_sup and h_sup)

    circ_ratio = round(circ / 5.0, 3)
    pass_fail = "PASS" if (circ >= 3.5 and supporting_ok) else "FAIL"

    return {
        "circularity_1to5": round(circ, 2),
        "circularity_ratio": circ_ratio,
        "supporting_material_ok": supporting_ok,
        "pass_fail": pass_fail,
        "geometry_risk": round(g.geometry_risk, 3),
        "min_dist_to_strut_um": round(g.min_dist_to_strut, 1),
        "min_dist_to_node_um": round(g.min_dist_to_node_center, 1),
        "nodes_inside_tool": g.nodes_inside_tool,
        "tool_pore_ratio": round(g.tool_pore_ratio, 2),
        "strut_intersection_um": round(g.strut_intersection_length, 1),
        "tool_x_um": tool_x,
        "tool_y_um": tool_y,
    }


def predict_grid(peak_current, pulse_on, duty, cfg: LatticeConfig | None = None, step_um=75):
    cfg = cfg or DEFAULT_CFG
    positions = grid_positions(cfg, step_um=step_um)
    circ, sup = [], []
    for p in positions:
        r = predict_at_point(peak_current, pulse_on, duty, p[0], p[1], cfg)
        circ.append(r["circularity_1to5"])
        sup.append(r["supporting_material_ok"])
    return {
        "positions": positions,
        "circularity": np.array(circ),
        "supporting_ok": np.array(sup),
        "step_um": step_um,
    }


def find_best_position(
    peak_current: float,
    pulse_on: float,
    duty: float,
    cfg: LatticeConfig,
    current_x: float,
    current_y: float,
    step_um: float | None = None,
) -> dict:
    """ML grid scan: best (x,y) for fixed EDM + geometry (location excluded)."""
    lo, hi = cfg.position_bounds()
    span = hi - lo
    if step_um is None:
        step_um = max(25.0, min(60.0, span / 18.0))

    grid = predict_grid(peak_current, pulse_on, duty, cfg, step_um=step_um)
    positions = grid["positions"]
    circ = grid["circularity"]
    sup = grid["supporting_ok"]

    bi = int(np.argmax(circ))
    bx, by = float(positions[bi][0]), float(positions[bi][1])
    best = predict_at_point(peak_current, pulse_on, duty, bx, by, cfg)

    pass_idx = np.where((circ >= 3.5) & sup)[0]
    pass_exists = len(pass_idx) > 0
    best_pass = None
    if pass_exists:
        pi = int(pass_idx[int(np.argmax(circ[pass_idx]))])
        px, py = float(positions[pi][0]), float(positions[pi][1])
        best_pass = predict_at_point(peak_current, pulse_on, duty, px, py, cfg)

    cur = predict_at_point(peak_current, pulse_on, duty, current_x, current_y, cfg)
    rec = best_pass if best_pass else best
    same_as_current = (
        abs(rec["tool_x_um"] - current_x) < step_um * 0.6
        and abs(rec["tool_y_um"] - current_y) < step_um * 0.6
    )

    return {
        "recommended_x_um": round(rec["tool_x_um"], 1),
        "recommended_y_um": round(rec["tool_y_um"], 1),
        "recommended_circularity_1to5": rec["circularity_1to5"],
        "recommended_circularity_ratio": rec["circularity_ratio"],
        "recommended_pass_fail": rec["pass_fail"],
        "recommended_supporting_ok": rec["supporting_material_ok"],
        "current_circularity_1to5": cur["circularity_1to5"],
        "current_pass_fail": cur["pass_fail"],
        "improvement_score": round(rec["circularity_1to5"] - cur["circularity_1to5"], 2),
        "pass_position_exists": pass_exists,
        "best_score_x_um": round(bx, 1),
        "best_score_y_um": round(by, 1),
        "best_score_circularity_1to5": best["circularity_1to5"],
        "grid_step_um": step_um,
        "grid_points_scanned": len(positions),
        "same_as_current": same_as_current,
        "explanation": _optimal_position_explanation(
            cur, rec, pass_exists, same_as_current, step_um,
        ),
    }


def _optimal_position_explanation(cur, rec, pass_exists, same_as_current, step_um) -> str:
    if same_as_current and cur["pass_fail"] == "PASS":
        return (
            "Your chosen position is already near-optimal for these EDM and geometry settings."
        )
    if same_as_current:
        return (
            f"No better position was found on the {step_um:.0f} µm scan grid. "
            "Circularity may be limited by EDM parameters or tool/pore geometry rather than position alone."
        )
    if pass_exists and rec["pass_fail"] == "PASS":
        return (
            f"Reposition the tool center to ({rec['tool_x_um']:.0f}, {rec['tool_y_um']:.0f}) µm "
            f"to improve circularity from {cur['circularity_1to5']:.2f}/5 to {rec['circularity_1to5']:.2f}/5 "
            f"and achieve PASS (keeping your current, pulse-on, duty, tool and pore settings fixed)."
        )
    if rec["circularity_1to5"] > cur["circularity_1to5"]:
        return (
            f"No position achieves PASS with these settings, but ({rec['tool_x_um']:.0f}, {rec['tool_y_um']:.0f}) µm "
            f"gives the best predicted circularity ({rec['circularity_1to5']:.2f}/5 vs your "
            f"{cur['circularity_1to5']:.2f}/5). Consider also adjusting EDM parameters."
        )
    return (
        "Your current position is among the best for these settings. "
        "Failure may be driven by aggressive EDM parameters or tool/pore size ratio."
    )
