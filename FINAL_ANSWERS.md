# FINAL ANSWERS — Lattice EDM Project

**Tool:** 900 µm | **Pore:** 235.6 µm | **Unit cell:** 500 µm | **Ratio:** 3.82×

**Goal:** Nearly circular white pore + **continuous black supporting ring**. Nodes may be destroyed.

**Only SEM success:** Run 4 → **4 A, 150 µs, 80 %**

---

## MASTER TABLE

| Case | Position | Images? | Peak current | Pulse-on | Duty |
|------|----------|---------|-------------|----------|------|
| Phase 1 | Unknown | No | 6 A | 50 µs | 64 % |
| **Phase 1** | **Unknown** | **Yes** | **4 A** | **150 µs** | **80 %** |
| Phase 2 | Known | No | 4–6 A | 75–150 µs | 64–80 % |
| **Phase 2** | **Known** | **Yes** | **4 / 3.5 A** | **150 µs** | **80 / 78 %** |

---

## Phase 1 — WITH images (FINAL)

| Parameter | Value |
|-----------|-------|
| Peak current | **4 A** (try 3.5 A) |
| Pulse-on time | **150 µs** |
| Duty factor | **80 %** |
| Servo feed | Very fine |
| Gap / flush | Stable, continuous |

## Phase 2 — WITH images (FINAL)

| Zone | I (A) | T (µs) | D (%) |
|------|-------|--------|-------|
| Pore center | 4 | 150 | 80 |
| Near strut | 3.5 | 150 | 78 |
| Near node (0,0) | 3.5 | 145 | 76 |

**Working area for tool:** 3×3 unit cells = **1500 × 1500 µm** (900 µm tool exceeds 500 µm cell).

---

## Pattern

- LOW current (4 A) + LONG pulse-on (150 µs) + HIGH duty (80 %)
- LOW removal (~0.5)
- Avoid I ≥ 8 A, T ≤ 75 µs, removal > 0.9

---

## Report paragraph

The lattice unit cell is 500 µm with pore diameter 235.6 µm. The 900 µm EDM tool gives ratio 3.82. Phase 1 (unknown position): **4 A, 150 µs, 80 %** (Run 4). Phase 2 (known x,y): same at center; **3.5 A** near struts. Without SEM, Run 5 (6 A, 50 µs, 64 %) is wrong for supporting boundary.

See `data/lattice_geometry.csv`, `data/recommended_trials.csv`, `outputs/FINAL_INPUTS_SUMMARY.json`.
