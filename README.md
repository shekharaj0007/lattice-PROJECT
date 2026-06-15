# Lattice EDM Project

## START HERE → [`FINAL_ANSWERS.md`](FINAL_ANSWERS.md)

## Problem

900 µm tool machines ~235.6 µm pore in 500 µm unit cell. Maximize **supporting-material boundary circularity**. Nodes may be damaged.

## Data

| File | Description |
|------|-------------|
| `data/original_16_runs.csv` | 16 real lab runs |
| `data/run_visual_labels.csv` | SEM labels |
| `data/lattice_geometry.csv` | Pore 235.6 µm, tool 900 µm |
| `synthetic_1100_points.csv` | AI-generated (not lab data) |
| `Lattice_EDM_Project_Report.docx` | Full Word report |

## Scripts

```bash
pip install -r requirements.txt
python phase1_model_actual.py
python generate_project_report.py
python predict_phase1.py --current 4 --pulse-on 150 --duty 80
```

## Lattice EDM Circularity Web App

**Double-click `RUN_SITE.bat`** or:

```bash
pip install -r requirements.txt
python web_server.py
```

Open **http://localhost:5050** — you should see **"UI v5"** in the top-right corner.

Do **not** use `streamlit run app.py` (disabled legacy app).

**Input:** Peak current, Pulse-on, Duty, tool diameter, pore, working area, tool position (x,y)  
**Output:** Circularity score, heatmap, synthetic lattice image, pass/fail for supporting material

Files: `web_server.py`, `lattice_geometry_engine.py`, `circularity_predictor.py`, `synthetic_view.py`

## Final answer (with SEM)

**4 A, 150 µs, 80 %** — Run 4

## Geometry

- Unit cell: 500 µm
- Pore: 235.6 µm  
- Tool: 900 µm
- Phase 2 working area: 1500×1500 µm (3×3 cells)
