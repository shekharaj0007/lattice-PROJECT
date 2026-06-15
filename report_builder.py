"""Build detailed analysis report with theory and pass/fail reasoning."""

from __future__ import annotations

from lattice_geometry_engine import LatticeConfig, GeometryFeatures

CIRCULARITY_PASS_THRESHOLD = 3.5  # on 1–5 scale
CIRCULARITY_RATIO_PASS = 0.70
GEOMETRY_RISK_PASS = 0.55


def edm_quality_score(I: float, T: float, D: float) -> tuple[float, str]:
    """Heuristic EDM gentleness from lab data (Run 4 = best)."""
    score = 0.0
    notes = []
    if I <= 5:
        score += 0.35
        notes.append(f"Peak current {I} A is in the gentle range (≤5 A favours intact supporting boundary).")
    elif I >= 8:
        score -= 0.35
        notes.append(f"Peak current {I} A is aggressive (≥8 A often destroys supporting material in SEM trials).")
    else:
        notes.append(f"Peak current {I} A is moderate.")

    if T >= 130:
        score += 0.35
        notes.append(f"Pulse-on {T} µs is long — stable, uniform erosion (Run 4 used 150 µs).")
    elif T <= 75:
        score -= 0.25
        notes.append(f"Pulse-on {T} µs is short — harsh sparks, irregular boundary risk.")

    if D >= 75:
        score += 0.2
        notes.append(f"Duty {D}% is high — supports finishing pass character.")
    elif D < 60:
        notes.append(f"Duty {D}% is relatively low.")

    label = "Excellent" if score >= 0.5 else "Good" if score >= 0.2 else "Moderate" if score >= 0 else "Aggressive"
    return score, label + " EDM setting. " + " ".join(notes)


def supporting_verdict(g: GeometryFeatures, cfg: LatticeConfig, I: float, T: float, D: float, ml_ok: bool) -> dict:
    reasons_pass = []
    reasons_fail = []

    if g.min_dist_to_strut >= 80 * (cfg.unit_cell_um / 500):
        reasons_pass.append(
            f"Tool center is {g.min_dist_to_strut:.1f} µm from nearest supporting strut — adequate clearance."
        )
    else:
        reasons_fail.append(
            f"Tool is only {g.min_dist_to_strut:.1f} µm from a strut — high risk of cutting supporting material."
        )

    if g.strut_intersection_length < 400 * (cfg.unit_cell_um / 500):
        reasons_pass.append(
            f"Estimated strut length inside tool circle ({g.strut_intersection_length:.0f} µm) is low."
        )
    else:
        reasons_fail.append(
            f"Tool circle intersects ~{g.strut_intersection_length:.0f} µm of strut length — boundary may break."
        )

    if cfg.tool_pore_ratio > 3.5:
        reasons_fail.append(
            f"Tool/pore ratio = {cfg.tool_pore_ratio:.2f} (>3.5) — tool much larger than pore; nodes/struts heavily engaged."
        )
    else:
        reasons_pass.append(f"Tool/pore ratio = {cfg.tool_pore_ratio:.2f} is within manageable range.")

    edm_score, edm_note = edm_quality_score(I, T, D)
    if edm_score >= 0.2:
        reasons_pass.append(edm_note)
    else:
        reasons_fail.append(edm_note)

    if g.geometry_risk <= GEOMETRY_RISK_PASS:
        reasons_pass.append(f"Geometry risk index {g.geometry_risk:.2f} ≤ {GEOMETRY_RISK_PASS} (acceptable).")
    else:
        reasons_fail.append(f"Geometry risk index {g.geometry_risk:.2f} > {GEOMETRY_RISK_PASS} (elevated).")

    if not ml_ok:
        reasons_fail.append("ML model predicts supporting boundary failure from combined EDM + position features.")

    ok = len(reasons_fail) == 0 or (ml_ok and g.geometry_risk <= GEOMETRY_RISK_PASS and edm_score >= 0)
    return {
        "verdict": "PASS" if ok else "FAIL",
        "reasons_pass": reasons_pass,
        "reasons_fail": reasons_fail,
    }


def circularity_verdict(circ_1to5: float, circ_ratio: float) -> dict:
    reasons_pass = []
    reasons_fail = []
    if circ_1to5 >= CIRCULARITY_PASS_THRESHOLD:
        reasons_pass.append(
            f"Circularity score {circ_1to5}/5 ≥ {CIRCULARITY_PASS_THRESHOLD} — nearly circular supporting boundary expected."
        )
    else:
        reasons_fail.append(
            f"Circularity score {circ_1to5}/5 < {CIRCULARITY_PASS_THRESHOLD} — boundary likely irregular."
        )
    if circ_ratio >= CIRCULARITY_RATIO_PASS:
        reasons_pass.append(
            f"Circularity ratio {circ_ratio:.2f} ≥ {CIRCULARITY_RATIO_PASS} — meets 70% of ideal circular shape."
        )
    else:
        reasons_fail.append(
            f"Circularity ratio {circ_ratio:.2f} < {CIRCULARITY_RATIO_PASS} — below pass threshold."
        )
    return {
        "pass_threshold_score": CIRCULARITY_PASS_THRESHOLD,
        "pass_threshold_ratio": CIRCULARITY_RATIO_PASS,
        "reasons_pass": reasons_pass,
        "reasons_fail": reasons_fail,
    }


def build_full_report(
    cfg: LatticeConfig,
    g: GeometryFeatures,
    peak_current: float,
    pulse_on: float,
    duty: float,
    tool_x: float,
    tool_y: float,
    circ_1to5: float,
    supporting_ok: bool,
    pass_fail: str,
    optimal_position: dict | None = None,
) -> dict:
    circ_ratio = round(circ_1to5 / 5.0, 3)
    circ_v = circularity_verdict(circ_1to5, circ_ratio)
    sup_v = supporting_verdict(g, cfg, peak_current, pulse_on, duty, supporting_ok)
    lo, hi = cfg.position_bounds()
    energy = peak_current * pulse_on * (duty / 100)
    pulse_off = pulse_on * (100 - duty) / max(duty, 1e-6)

    return {
        "summary": {
            "overall": pass_fail,
            "circularity_1to5": circ_1to5,
            "circularity_ratio": circ_ratio,
            "supporting_material": "PASS" if supporting_ok else "FAIL",
        },
        "pass_criteria": {
            "circularity_score_min": CIRCULARITY_PASS_THRESHOLD,
            "circularity_ratio_min": CIRCULARITY_RATIO_PASS,
            "geometry_risk_max": GEOMETRY_RISK_PASS,
            "rule": "PASS requires circularity ≥ 3.5 AND ratio ≥ 0.70 AND supporting material intact.",
        },
        "user_inputs": {
            "peak_current_A": peak_current,
            "pulse_on_us": pulse_on,
            "duty_pct": duty,
            "tool_diameter_um": cfg.tool_diameter_um,
            "pore_diameter_um": cfg.pore_diameter_um,
            "working_area_um": cfg.working_area_um,
            "tool_x_um": tool_x,
            "tool_y_um": tool_y,
            "valid_x_range": [lo, hi],
            "valid_y_range": [lo, hi],
        },
        "geometry_analysis": {
            "unit_cell_um": cfg.unit_cell_um,
            "tool_pore_ratio": round(cfg.tool_pore_ratio, 2),
            "geometry_risk": g.geometry_risk,
            "min_dist_to_strut_um": g.min_dist_to_strut,
            "min_dist_to_node_um": g.min_dist_to_node_center,
            "nodes_inside_tool": g.nodes_inside_tool,
            "strut_intersection_um": g.strut_intersection_length,
            "pore_overlap_fraction": round(g.pore_overlap_fraction, 3),
            "why_position_range": (
                f"Tool radius = {cfg.tool_radius:.0f} µm. Center must stay [{lo:.0f}, {hi:.0f}] µm "
                f"so the full {cfg.tool_diameter_um:.0f} µm circle remains inside the "
                f"{cfg.working_area_um:.0f}×{cfg.working_area_um:.0f} µm working area."
            ),
        },
        "derived_edm": {
            "discharge_energy_proxy": round(energy, 1),
            "pulse_off_us": round(pulse_off, 1),
        },
        "circularity_explanation": circ_v,
        "supporting_explanation": sup_v,
        "mathematics": {
            "position_bounds_formula": "x_valid in [R, W - R] where R = tool_diameter/2, W = working_area",
            "position_bounds_values": [lo, hi],
            "tool_pore_ratio_formula": "tool_diameter / pore_diameter",
            "discharge_energy_formula": "I × T × (D/100)",
            "pulse_off_formula": "T × (100 - D) / D",
            "geometry_risk_formula": "0.5×strut_proximity + 0.3×strut_intersection + 0.2×tool_pore_factor",
            "circularity_ratio_formula": "circularity_score / 5",
        },
        "decision_tree": [
            f"Step 1: Circularity score {circ_1to5}/5 — need ≥ {CIRCULARITY_PASS_THRESHOLD}",
            f"Step 2: Circularity ratio {circ_ratio} — need ≥ {CIRCULARITY_RATIO_PASS}",
            f"Step 3: Supporting material — {'intact' if supporting_ok else 'predicted failure'}",
            f"Step 4: Geometry risk {g.geometry_risk:.2f} — prefer ≤ {GEOMETRY_RISK_PASS}",
            f"Step 5: Overall = {'PASS' if pass_fail == 'PASS' else 'FAIL'}",
        ],
        "theory_notes": [
            "Black region = supporting material (must form continuous circular ring).",
            "Red nodes = fixed-size strut junctions (~235.6 µm); white circles = pores (scale with your pore diameter input).",
            "Red nodes may be destroyed — that is acceptable.",
            f"Reference lab success: Run 4 — 4 A, 150 µs, 80 % (tool 900 µm in original experiments).",
            "ML trained on 16 SEM-labelled experiments + geometry-augmented grid.",
            f"Your pore {cfg.pore_diameter_um} µm, tool {cfg.tool_diameter_um} µm, work area {cfg.working_area_um} µm.",
            f"Tool/pore ratio {cfg.tool_pore_ratio:.2f} — values >3.5 increase strut damage risk.",
        ],
        "optimal_position": optimal_position or {},
    }
