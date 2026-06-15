"""Phase 1 model — 16 + synthetic data (exploratory)."""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score

ROOT = Path(__file__).resolve().parent
INPUT_COLS = ["Peak_Current_A", "Pulse_On_Time_us", "Duty_Factor_pct"]


def circularity_score(top, bottom):
    return (top + bottom) / 2.0 + 0.5 * abs(top - bottom)


def load_dataset():
    rows = []
    with open(ROOT / "data" / "original_16_runs.csv") as f:
        for r in csv.DictReader(f):
            rows.append({k: float(r[k]) if k != "Run" else int(r[k]) for k in r})
    with open(ROOT / "synthetic_1100_points.csv") as f:
        for r in csv.DictReader(f):
            rows.append({k: float(r[k]) if k != "source" else r["source"] for k in r})
    return rows


def engineer_features(X):
    i, t, d = X[:, 0], X[:, 1], X[:, 2]
    return np.column_stack([X, i*t*(d/100), t*(100-d)/d, i*d, t/(d+1e-6), i**2, t**2])


def build_matrix(rows):
    X = engineer_features(np.array([[r[c] for c in INPUT_COLS] for r in rows]))
    return X, np.array([r["Hole_Dev_Top_um"] for r in rows]), np.array([r["Hole_Dev_Bottom_um"] for r in rows])


def train_models(X, y_top, y_bot):
    models = {}
    for name, y in [("top", y_top), ("bottom", y_bot)]:
        gb = GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.08, random_state=42)
        gb.fit(X, y)
        cv = cross_val_score(gb, X, y, cv=5, scoring="neg_mean_absolute_error")
        models[name] = {"model": gb, "cv_mae": float(-cv.mean())}
    return models


def grid_search_recommendations(model_top, model_bot, n=5000):
    rng = np.random.default_rng(42)
    c = np.column_stack([rng.uniform(4,10,n), rng.uniform(50,150,n), rng.uniform(56,80,n)])
    Xc = engineer_features(c)
    pt, pb = model_top.predict(Xc), model_bot.predict(Xc)
    circ = np.array([circularity_score(a,b) for a,b in zip(pt,pb)])
    return [{"Peak_Current_A": round(float(c[i,0]),2), "Pulse_On_Time_us": round(float(c[i,1]),1),
             "Duty_Factor_pct": round(float(c[i,2]),1), "predicted_circularity_score": round(float(circ[i]),2)}
            for i in np.argsort(circ)[:20]]


def main():
    rows = load_dataset()
    X, y_top, y_bot = build_matrix(rows)
    models = train_models(X, y_top, y_bot)
    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)
    import joblib
    joblib.dump(models, out_dir / "phase1_model.joblib")
    recs = grid_search_recommendations(models["top"]["model"], models["bottom"]["model"])
    with open(out_dir / "phase1_recommendations.json", "w") as f:
        json.dump({"model": "GradientBoosting", "top_20_parameter_sets": recs}, f, indent=2)
    print(f"Saved recommendations. CV MAE top: {models['top']['cv_mae']:.1f} um")


if __name__ == "__main__":
    main()
