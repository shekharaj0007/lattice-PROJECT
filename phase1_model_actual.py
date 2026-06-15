"""
Phase 1 — 16 real lab runs.

SUCCESS = maximum circularity of SUPPORTING MATERIAL boundary (SEM judgment).
REFERENCE = Run 4 (4 A, 150 us, 80 %) — only clear success in your images.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parent
INPUT_COLS = ["Peak_Current_A", "Pulse_On_Time_us", "Duty_Factor_pct"]
TARGET_RUN = 4


def load_original():
    rows = []
    with open(ROOT / "data" / "original_16_runs.csv") as f:
        for r in csv.DictReader(f):
            rows.append({k: float(r[k]) if k != "Run" else int(r[k]) for k in r})
    return rows


def load_visual_labels():
    labels = {}
    with open(ROOT / "data" / "run_visual_labels.csv") as f:
        for r in csv.DictReader(f):
            labels[int(r["Run"])] = {
                "boundary_circularity": int(r["Boundary_circularity_1to5"]),
                "supporting_intact": int(r["Supporting_boundary_intact"]),
                "notes": r["Notes"],
            }
    return labels


def build_poly_features(rows):
    X = np.array([[r[c] for c in INPUT_COLS] for r in rows])
    return PolynomialFeatures(degree=2, include_bias=False).fit_transform(X)


def loocv_predict_circularity(rows, labels):
    X = build_poly_features(rows)
    y = np.array([labels[int(r["Run"])]["boundary_circularity"] for r in rows])
    loo = LeaveOneOut()
    preds = np.zeros_like(y, dtype=float)
    for train_idx, test_idx in loo.split(X):
        m = Ridge(alpha=0.5)
        m.fit(X[train_idx], y[train_idx])
        preds[test_idx] = np.clip(m.predict(X[test_idx]), 1, 5)
    return preds, mean_absolute_error(y, preds), y


def rank_by_visual(rows, labels):
    out = []
    for r in rows:
        run = int(r["Run"])
        lb = labels[run]
        out.append({
            "Run": run,
            "Peak_Current_A": r["Peak_Current_A"],
            "Pulse_On_Time_us": r["Pulse_On_Time_us"],
            "Duty_Factor_pct": r["Duty_Factor_pct"],
            "Hole_Dev_Top_um": r["Hole_Dev_Top_um"],
            "Hole_Dev_Bottom_um": r["Hole_Dev_Bottom_um"],
            "boundary_circularity_1to5": lb["boundary_circularity"],
            "supporting_boundary_intact": lb["supporting_intact"],
            "is_reference_success": run == TARGET_RUN,
            "notes": lb["notes"],
        })
    return sorted(out, key=lambda x: (-x["boundary_circularity_1to5"], -x["supporting_boundary_intact"]))


def gp_maximize_circularity(rows, labels, n_grid=3000):
    X = np.array([[r[c] for c in INPUT_COLS] for r in rows])
    y = np.array([labels[int(r["Run"])]["boundary_circularity"] for r in rows])
    gp = GaussianProcessRegressor(
        kernel=Matern(nu=2.5) + WhiteKernel(noise_level=0.3),
        normalize_y=True, random_state=42,
    )
    gp.fit(X, y)
    rng = np.random.default_rng(42)
    candidates = []
    for _ in range(n_grid // 2):
        candidates.append([rng.uniform(3.5, 5.5), rng.uniform(120, 150), rng.uniform(75, 80)])
    for _ in range(n_grid // 2):
        candidates.append([rng.uniform(4, 10), rng.uniform(50, 150), rng.uniform(56, 80)])
    candidates = np.array(candidates)
    mu, std = gp.predict(candidates, return_std=True)
    order = np.argsort(-(mu + 0.15 * std))
    return [{
        "Peak_Current_A": round(float(candidates[i, 0]), 2),
        "Pulse_On_Time_us": round(float(candidates[i, 1]), 1),
        "Duty_Factor_pct": round(float(candidates[i, 2]), 1),
        "predicted_boundary_circularity_1to5": round(float(mu[i]), 2),
        "uncertainty": round(float(std[i]), 3),
    } for i in order[:15]]


def main():
    rows = load_original()
    labels = load_visual_labels()
    print("PHASE 1 — Goal: MAXIMUM circularity of SUPPORTING MATERIAL boundary")
    print("Reference: Run 4 -> 4 A, 150 us, 80 %")
    preds, mae, y_true = loocv_predict_circularity(rows, labels)
    print(f"LOOCV MAE circularity: {mae:.2f}")
    ranked = rank_by_visual(rows, labels)
    print("\nBest runs:")
    for i, r in enumerate(ranked[:5], 1):
        print(f"{i}. Run {r['Run']}: {r['Peak_Current_A']}A, {r['Pulse_On_Time_us']}us, {r['Duty_Factor_pct']}%")
    recs = gp_maximize_circularity(rows, labels)
    out = ROOT / "outputs" / "phase1_actual_only.json"
    out.parent.mkdir(exist_ok=True)
    ref = next(r for r in rows if int(r["Run"]) == TARGET_RUN)
    with open(out, "w") as f:
        json.dump({
            "success_criterion": "Maximize circularity of supporting-material boundary. Run 4 SEM reference.",
            "reference_run": TARGET_RUN,
            "reference_parameters": {"Peak_Current_A": 4, "Pulse_On_Time_us": 150, "Duty_Factor_pct": 80},
            "ranking_by_SEM": ranked,
            "gp_recommendations_maximize_circularity": recs,
            "loocv_mae_circularity_1to5": mae,
        }, f, indent=2)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
