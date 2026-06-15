"""
Interactive prediction for Phase 1.
Usage: python predict_phase1.py --current 4 --pulse-on 150 --duty 80
"""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from phase1_model import engineer_features, circularity_score, load_dataset, build_matrix, train_models

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "outputs" / "phase1_model.joblib"


def predict(peak_current: float, pulse_on: float, duty: float):
    if not MODEL_PATH.exists():
        rows = load_dataset()
        X, y_top, y_bot = build_matrix(rows)
        models = train_models(X, y_top, y_bot)
        joblib.dump(models, MODEL_PATH)
    else:
        models = joblib.load(MODEL_PATH)
    X = engineer_features(np.array([[peak_current, pulse_on, duty]]))
    top = float(models["top"]["model"].predict(X)[0])
    bot = float(models["bottom"]["model"].predict(X)[0])
    return {
        "inputs": {"Peak_Current_A": peak_current, "Pulse_On_Time_us": pulse_on, "Duty_Factor_pct": duty},
        "predicted_Hole_Dev_Top_um": round(top, 2),
        "predicted_Hole_Dev_Bottom_um": round(bot, 2),
        "circularity_score": round(circularity_score(top, bot), 2),
        "interpretation": "For MAXIMUM supporting-boundary circularity use Run 4: 4 A, 150 us, 80 %. See FINAL_ANSWERS.md.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current", type=float, required=True)
    p.add_argument("--pulse-on", type=float, required=True)
    p.add_argument("--duty", type=float, required=True)
    args = p.parse_args()
    print(json.dumps(predict(args.current, args.pulse_on, args.duty), indent=2))


if __name__ == "__main__":
    main()
