"""Phase 1 analysis: EDM parameter prediction without tool position."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def circularity_score(top: float, bottom: float) -> float:
    return (top + bottom) / 2.0 + 0.5 * abs(top - bottom)


def load_original():
    rows = []
    with open(ROOT / "data" / "original_16_runs.csv") as f:
        for r in csv.DictReader(f):
            rows.append({k: float(r[k]) if k != "Run" else int(r[k]) for k in r})
    return rows


def main():
    rows = load_original()
    ranked = sorted(rows, key=lambda r: circularity_score(r["Hole_Dev_Top_um"], r["Hole_Dev_Bottom_um"]))
    print("Original 16 — best deviation score (NOT same as SEM circularity):")
    for r in ranked[:5]:
        s = circularity_score(r["Hole_Dev_Top_um"], r["Hole_Dev_Bottom_um"])
        print(f"Run {int(r['Run'])}: score={s:.1f} ({r['Peak_Current_A']}A, {r['Pulse_On_Time_us']}us, {r['Duty_Factor_pct']}%)")


if __name__ == "__main__":
    main()
