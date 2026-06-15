LatticeFlow — EDM Lattice Circularity Predictor

LIVE DEPLOYMENT AT ------https://lattice-project.onrender.com/


Predict the circularity of EDM-machined holes in metallic lattice structures using Machine Learning, Gaussian Process Regression, and geometric analysis.




What This Project Does

A 900 µm EDM tool is inserted into the pore of a metallic lattice structure. The pore is only 235.6 µm in diameter — meaning the tool is 3.82× bigger than the pore and simultaneously touches the pore, nodes, and supporting struts all at once.

The goal is to find EDM parameters and tool landing positions such that:


The supporting material (black struts) survives as a complete, nearly circular ring
The nodes (red circles) may be destroyed — that is acceptable
The machined hole (white region) is as circular as possible


The project builds a web application where you input any EDM parameters and tool position, and it predicts the circularity at that point across the entire lattice grid.


The Problem — Visualised

LATTICE STRUCTURE (500×500 µm unit cell)
┌─────────────────────────────┐
│  ●  ───────────────────  ●  │   ● = Node (235.6 µm diameter) — CAN be destroyed
│  │   ○   ───   ○   ───  │  │   ○ = Open pore (235.6 µm diameter)
│  │  supporting material  │  │   ─ = Supporting strut — MUST survive as circular ring
│  ●  ───────────────────  ●  │
└─────────────────────────────┘

EDM TOOL (900 µm diameter) → dropped anywhere in the lattice
→ Tool is 3.82× the pore size
→ Cannot fit inside one pore — machines pore + nodes + struts simultaneously
→ Challenge: keep supporting ring circular despite tool massively overfilling pore

Phase 1: Tool insertion position is unknown — find robust EDM parameters that work anywhere.

Phase 2: Tool position A(x, y) is known — optimise parameters per landing zone.


Key Finding from 16 Lab Experiments

Out of 16 real EDM trials, only Run 4 produced a circular supporting boundary in SEM images:

RunPeak CurrentPulse-on TimeDuty FactorSEM Result44 A150 µs80 %✅ PASS — circular boundary56 A50 µs64 %❌ FAIL — best deviation score but struts destroyed9–168–10 Avariousvarious❌ FAIL — high current blasts supporting material

The paradox: Run 5 has the best numerical deviation score but completely fails the SEM test. Run 4 has a high deviation score but is the only visual success. This is why SEM image analysis — not numerical deviation — is the true success metric.

Why Run 4 works:


Low current (4 A) → small, controlled plasma channel
Long pulse (150 µs) → stable, diffused erosion in all radial directions uniformly
High duty (80 %) → steady continuous removal → symmetric circular boundary
Discharge energy = 4 × 150 × 0.80 = 480 units (2.5× more than Run 5's 192, but delivered gently)



Lattice Geometry

ParameterValueSourceUnit cell (square side)500 µmSEM scale barPore diameter235.6 µmDerived: 3x = 500√2 → x = 235.6 µmNode diameter235.6 µmAssumed equal to pore (physical lattice)Tool tip diameter900 µmLab specificationTool / pore ratio3.82×900 / 235.6Working area (Phase 2)1500 × 1500 µm3×3 unit cells (tool exceeds single 500 µm cell)

Pore diameter derivation:

Unit cell diagonal = 500 × √2 = 707.1 µm
Diagonal = node_radius + pore_diameter + node_radius = 3x
∴ 3x = 500√2   →   x = 235.6 µm

Why 3×3 working area?

The tool radius (450 µm) exceeds the entire unit cell (500 µm). When dropped anywhere, the tool overlaps multiple unit cells. A 3×3 grid (1500×1500 µm) captures the full tool footprint from any landing position.


Web Application

Quick Start (Windows)

Double-click  RUN_SITE.bat

Then open http://localhost:5050

Manual Start

bashpip install -r requirements.txt
python web_server.py

Open http://localhost:5050 — look for "UI v5" badge top-right.


⚠️ Do NOT use streamlit run app.py — that version is disabled.



What You Can Do

1. Single Point Analysis


Enter EDM parameters: Peak current (A), Pulse-on time (µs), Duty factor (%)
Enter tool geometry: tool diameter, pore diameter, working area
Enter tool landing position: X, Y (µm from bottom-left origin)
Get: circularity score (1–5), PASS/FAIL, synthetic lattice image, full engineering report


2. Grid Scan (Heatmap)


Same EDM parameters as above
Scans all valid tool positions in the working area
Generates a colour heatmap: green = high circularity, red = low circularity
Finds the best (x, y) position for your chosen parameters


3. LLM Chat Assistant


Ask questions about your analysis results
Get explanations of why a position passed or failed
Recommendations for improving circularity


Pass Criteria

CriterionThresholdCircularity score≥ 3.5 / 5.0Circularity ratio≥ 0.70Supporting materialIntact (not destroyed)Geometry risk≤ 0.55

All four must be met for PASS.


Project Structure

lattice-edm/
│
├── web_server.py              # Flask web server — main entry point
├── lattice_geometry_engine.py # Core geometry: nodes, pores, struts, distances
├── circularity_predictor.py   # ML model: GradientBoosting + geometry heuristic
├── synthetic_view.py          # Matplotlib lattice visualisation + heatmap
├── chat_assistant.py          # LLM chat (Anthropic / OpenAI)
├── report_builder.py          # Full engineering report generator
├── app.py                     # Legacy Streamlit (disabled)
│
├── phase1_model_actual.py     # Phase 1: GP on 16 real runs (for report)
├── phase1_model.py            # Phase 1: GB on 16 + 1100 synthetic (exploratory)
├── phase1_analysis.py         # Phase 1: deviation score ranking
├── predict_phase1.py          # CLI prediction tool
│
├── generate_project_report.py # Generates Word (.docx) report
├── edm_lattice_predictor.html # Standalone HTML predictor (no server needed)
│
├── data/
│   ├── original_16_runs.csv   # 16 real lab experiments (ground truth)
│   ├── run_visual_labels.csv  # SEM circularity labels per run
│   ├── lattice_geometry.csv   # Geometry constants
│   └── recommended_trials.csv # Suggested next experiments
│
├── synthetic_1100_points.csv  # AI-generated synthetic data (NOT lab data)
│
├── render.yaml                # Render.com deployment config
├── Procfile                   # Gunicorn start command
├── requirements.txt           # Python dependencies
├── RUN_SITE.bat               # Windows quick-start
├── .env.example               # API key template
└── .gitignore


ML Model

Training Data


16 real lab runs (ground truth) — each labelled from SEM images (1–5 circularity scale)
1100 AI-generated synthetic points (augmentation only — not independent lab data)
Geometry features computed for every grid position in the working area


Features

EDM features:   Peak current, Pulse-on, Duty, Discharge energy, Pulse-off, I×D, T/D
Geometry:       Distance to nearest strut, Distance to nearest node,
                Nodes inside tool, Pores overlapped, Strut intersection length,
                Pore overlap fraction, Node overlap fraction, Geometry risk index,
                Tool/pore ratio, Working area, Tool diameter

Model Architecture


GradientBoostingRegressor (120 estimators) → predicts circularity score (1–5)
GradientBoostingRegressor (80 estimators) → predicts supporting material intact (0/1)
Physics heuristic blend — weighted by how much config differs from training data
Gaussian Process (Phase 1) — Matérn 5/2 kernel, LOOCV on 16 real points


Validation


Leave-One-Out Cross Validation (LOOCV) on 16 real points
LOO MAE ≈ 0.5 / 5.0 scale
LOO R² = 0.091 (small dataset — use as guide, not absolute truth)



CLI Tools

bash# Predict circularity at specific EDM parameters
python predict_phase1.py --current 4 --pulse-on 150 --duty 80

# Run Phase 1 analysis (GP on 16 real runs)
python phase1_model_actual.py

# Run Phase 1 exploratory model (16 + synthetic)
python phase1_model.py

# Generate Word report
python generate_project_report.py


Deploy to Render.com


Push this repo to GitHub
Go to render.com → New → Web Service
Connect your GitHub repo
Render auto-detects render.yaml — no manual config needed
Add environment variable: ANTHROPIC_API_KEY = sk-ant-...
Your live URL: https://your-app-name.onrender.com



Environment Variables

Copy .env.example to .env and fill in your key:

envANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Or use OpenAI:
# OPENAI_API_KEY=sk-your-key-here
# OPENAI_MODEL=gpt-4o-mini


⚠️ Never commit .env to GitHub. It is already in .gitignore.




Final Answers

Phase 1 — Tool Position Unknown

ParameterValuePeak current4 APulse-on time150 µsDuty factor80 %Discharge energy480 unitsPulse-off time37.5 µs

Additional machine settings: very fine servo feed (1–5 µm/step), stable low gap voltage, continuous dielectric flushing, freshly dressed 900 µm electrode.

Phase 2 — Tool Position Known

ZoneCurrentPulse-onDutyPore center4 A150 µs80 %Mid pore4 A148 µs79 %Near strut3.5 A150 µs78 %Near node (0,0)3.5 A145 µs76 %

Without SEM Images (Wrong Answer)


6 A, 50 µs, 64 % — minimises deviation score (Run 5) but destroys supporting material in SEM. Do not use.




Data Sources

SourceCountRoleLab experiments16Ground truth — real EDM trialsSEM images (1–16)16Visual proof — only truth of boundary circularityoriginal_16_runs.csv16Numerical data from labsynthetic_1100_points.csv1100AI-generated augmentation — NOT independent lab data


Requirements

Python 3.11+
numpy, scikit-learn, pandas, matplotlib
flask, gunicorn
Pillow, python-docx, joblib

Install: pip install -r requirements.txt


References


Phase 1 notebook pages (15 June 2026): Grid subdivision logic, working area = 5000×10,000 µm divided into 500 µm cells, intersection points as prediction targets
Lab reference: Run 4 — 4 A, 150 µs, 80 % (only SEM success in 16 trials)
Geometry: 3x = 500√2, pore = node = 235.6 µm, tool/pore ratio = 3.82
ML target: Maximize boundary circularity of supporting material — NOT minimize hole deviation
