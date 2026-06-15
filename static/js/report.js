const raw = sessionStorage.getItem("latticeReport");
const body = document.getElementById("report-body");
const meta = document.getElementById("report-meta");
const headerVerdict = document.getElementById("header-verdict");

if (!raw) {
  body.innerHTML = "<p class='loading'>No report data. Run an analysis on the main page, then click <strong>Please click here for the detailed report</strong>.</p>";
} else {
  const { report: r, image } = JSON.parse(raw);
  const pass = r.summary.overall === "PASS";
  meta.textContent = `Generated ${new Date().toLocaleString()} · Circularity ${r.summary.circularity_1to5}/5 · Ratio ${r.summary.circularity_ratio}`;
  headerVerdict.className = `header-verdict ${pass ? "pass" : "fail"}`;
  headerVerdict.textContent = pass
    ? "OVERALL PASS — Supporting boundary expected circular and intact"
    : "OVERALL FAIL — See sections below for corrective guidance";

  const sec = (title, html) => `<div class="section"><h2>${title}</h2>${html}</div>`;
  const m = r.mathematics || {};
  const g = r.geometry_analysis;
  const u = r.user_inputs;

  body.innerHTML = [
    sec("1. Executive Summary", `
      <div class="summary-grid">
        <div class="summary-item"><strong>Overall result</strong><span class="${pass ? "pass" : "fail"}">${r.summary.overall}</span></div>
        <div class="summary-item"><strong>Circularity score</strong><span>${r.summary.circularity_1to5} / 5</span></div>
        <div class="summary-item"><strong>Circularity ratio</strong><span>${r.summary.circularity_ratio}</span></div>
        <div class="summary-item"><strong>Supporting material</strong><span class="${r.summary.supporting_material === "PASS" ? "pass" : "fail"}">${r.summary.supporting_material}</span></div>
      </div>
      ${image ? `<img class="report-img" src="data:image/png;base64,${image}" alt="Synthetic lattice view"/>` : ""}
      <p style="margin-top:1rem;font-size:0.9rem;color:#64748b">This report explains <em>why</em> your configuration passes or fails, using geometry mathematics and ML trained on 16 SEM-labelled lab experiments.</p>
    `),

    sec("2. Pass / Fail Criteria (thresholds)", `
      <table>
        <tr><th>Criterion</th><th>Required</th><th>Your result</th><th>Status</th></tr>
        <tr>
          <td>Circularity score</td><td>≥ ${r.pass_criteria.circularity_score_min} / 5</td>
          <td>${r.summary.circularity_1to5}</td>
          <td class="${r.summary.circularity_1to5 >= r.pass_criteria.circularity_score_min ? "pass" : "fail"}">${r.summary.circularity_1to5 >= r.pass_criteria.circularity_score_min ? "OK" : "FAIL"}</td>
        </tr>
        <tr>
          <td>Circularity ratio</td><td>≥ ${r.pass_criteria.circularity_ratio_min}</td>
          <td>${r.summary.circularity_ratio}</td>
          <td class="${r.summary.circularity_ratio >= r.pass_criteria.circularity_ratio_min ? "pass" : "fail"}">${r.summary.circularity_ratio >= r.pass_criteria.circularity_ratio_min ? "OK" : "FAIL"}</td>
        </tr>
        <tr>
          <td>Geometry risk index</td><td>≤ ${r.pass_criteria.geometry_risk_max}</td>
          <td>${g.geometry_risk}</td>
          <td class="${g.geometry_risk <= r.pass_criteria.geometry_risk_max ? "pass" : "fail"}">${g.geometry_risk <= r.pass_criteria.geometry_risk_max ? "OK" : "HIGH"}</td>
        </tr>
        <tr>
          <td>Supporting material</td><td>Intact circular boundary</td>
          <td>${r.summary.supporting_material}</td>
          <td class="${r.summary.supporting_material === "PASS" ? "pass" : "fail"}">${r.summary.supporting_material}</td>
        </tr>
      </table>
      <p style="margin-top:0.85rem"><strong>Rule:</strong> ${r.pass_criteria.rule}</p>
      <p style="font-size:0.88rem;color:#64748b;margin-top:0.5rem">Circularity ratio = score ÷ 5. A ratio of 0.70 means the machined boundary achieves at least 70% of ideal circular shape. Nodes (red) may be destroyed; the black supporting ring must remain continuous.</p>
    `),

    sec("3. Your manual inputs", `
      <table>
        <tr><td>Peak current</td><td><strong>${u.peak_current_A} A</strong></td></tr>
        <tr><td>Pulse-on time</td><td><strong>${u.pulse_on_us} µs</strong></td></tr>
        <tr><td>Duty factor</td><td><strong>${u.duty_pct} %</strong></td></tr>
        <tr><td>Tool diameter (user selected)</td><td><strong>${u.tool_diameter_um} µm</strong></td></tr>
        <tr><td>Pore diameter (user entered)</td><td><strong>${u.pore_diameter_um} µm</strong></td></tr>
        <tr><td>Working area (user entered)</td><td><strong>${u.working_area_um} × ${u.working_area_um} µm</strong></td></tr>
        <tr><td>Tool center position</td><td><strong>(${u.tool_x_um}, ${u.tool_y_um}) µm</strong></td></tr>
        <tr><td>Valid X range</td><td>${u.valid_x_range[0]} – ${u.valid_x_range[1]} µm</td></tr>
        <tr><td>Valid Y range</td><td>${u.valid_y_range[0]} – ${u.valid_y_range[1]} µm</td></tr>
      </table>
    `),

    sec("4. Recommended tool position (ML grid scan)", (() => {
      const o = r.optimal_position || {};
      if (!o.recommended_x_um) {
        return "<p>Position optimization data not available for this run.</p>";
      }
      const improved = o.improvement_score > 0;
      const recPass = o.recommended_pass_fail === "PASS";
      return `
        <p style="margin-bottom:0.85rem">
          Your <strong>current</strong>, pulse-on, duty, tool diameter, pore diameter, and working area are held fixed.
          The ML model scanned <strong>${o.grid_points_scanned}</strong> positions (${o.grid_step_um} µm grid)
          to find the best tool center (x, y) for maximum circularity.
        </p>
        <table>
          <tr><th></th><th>Your position</th><th>Recommended position</th></tr>
          <tr>
            <td>Coordinates (µm)</td>
            <td><strong>(${u.tool_x_um}, ${u.tool_y_um})</strong></td>
            <td><strong>(${o.recommended_x_um}, ${o.recommended_y_um})</strong></td>
          </tr>
          <tr>
            <td>Circularity score /5</td>
            <td>${o.current_circularity_1to5}</td>
            <td class="${recPass ? "pass" : improved ? "" : "fail"}">${o.recommended_circularity_1to5}</td>
          </tr>
          <tr>
            <td>Circularity ratio</td>
            <td>${r.summary.circularity_ratio}</td>
            <td>${o.recommended_circularity_ratio}</td>
          </tr>
          <tr>
            <td>Overall</td>
            <td class="${pass ? "pass" : "fail"}">${o.current_pass_fail}</td>
            <td class="${recPass ? "pass" : "fail"}">${o.recommended_pass_fail}</td>
          </tr>
          <tr>
            <td>Supporting material</td>
            <td>${r.summary.supporting_material}</td>
            <td>${o.recommended_supporting_ok ? "PASS" : "FAIL"}</td>
          </tr>
        </table>
        <div class="formula-block" style="margin-top:1rem">
          <strong>Recommendation:</strong> ${o.explanation}
        </div>
        ${!recPass ? `<p style="margin-top:0.75rem;font-size:0.88rem;color:#64748b">
          No grid point achieved PASS with your current EDM settings.
          Best achievable score at (${o.best_score_x_um}, ${o.best_score_y_um}) µm is ${o.best_score_circularity_1to5}/5.
          Consider gentler settings (e.g. 4 A, 150 µs, 80 %) in addition to repositioning.
        </p>` : ""}
        <p style="margin-top:0.75rem;font-size:0.88rem;color:#64748b">
          Enter the recommended coordinates in the main app and click <strong>Analyze</strong> again to verify.
        </p>
      `;
    })()),

    sec("5. Mathematics & geometry", `
      <h3>Why position range changes with tool size</h3>
      <p>${g.why_position_range}</p>
      <div class="formula-block">
        ${m.position_bounds_formula || "x_valid ∈ [R, W − R]"}<br/>
        R = tool_diameter / 2 = ${u.tool_diameter_um / 2} µm<br/>
        W = working_area = ${u.working_area_um} µm<br/>
        Valid range = [${u.valid_x_range[0]}, ${u.valid_x_range[1]}] µm
      </div>
      <h3>Key ratios & derived EDM quantities</h3>
      <div class="formula-block">
        Tool / pore ratio = ${g.tool_pore_ratio}  (${m.tool_pore_ratio_formula || "tool / pore"})<br/>
        Discharge energy proxy = ${r.derived_edm.discharge_energy_proxy}  (${m.discharge_energy_formula || "I×T×D/100"})<br/>
        Pulse-off time = ${r.derived_edm.pulse_off_us} µs  (${m.pulse_off_formula || "T×(100−D)/D"})<br/>
        Circularity ratio = ${r.summary.circularity_ratio}  (${m.circularity_ratio_formula || "score/5"})
      </div>
      <table>
        <tr><td>Unit cell (derived)</td><td>${g.unit_cell_um} µm</td></tr>
        <tr><td>Min distance to supporting strut</td><td>${g.min_dist_to_strut_um} µm</td></tr>
        <tr><td>Min distance to node center</td><td>${g.min_dist_to_node_um} µm</td></tr>
        <tr><td>Nodes inside tool circle</td><td>${g.nodes_inside_tool}</td></tr>
        <tr><td>Strut length inside tool</td><td>${g.strut_intersection_um} µm</td></tr>
        <tr><td>Pore overlap fraction</td><td>${g.pore_overlap_fraction}</td></tr>
        <tr><td>Geometry risk index</td><td>${g.geometry_risk}</td></tr>
      </table>
      <p style="font-size:0.88rem;color:#64748b;margin-top:0.75rem">Geometry risk combines strut proximity, strut intersection length inside the tool circle, and tool/pore size ratio. When tool diameter exceeds pore size (ratio > 1), the tool necessarily engages nodes and struts — gentle EDM settings are critical.</p>
    `),

    sec("6. Decision logic (step-by-step)", `
      <ol class="decision-list">${(r.decision_tree || []).map(s => `<li>${s.replace(/^Step \\d+: /, "")}</li>`).join("")}</ol>
    `),

    sec("7. Circularity analysis — detailed reasons", `
      <h3>Factors supporting circularity</h3>
      <ul class="reasons pass">${r.circularity_explanation.reasons_pass.map(x => `<li>${x}</li>`).join("") || "<li>None identified</li>"}</ul>
      <h3>Factors reducing circularity</h3>
      <ul class="reasons fail">${r.circularity_explanation.reasons_fail.map(x => `<li>${x}</li>`).join("") || "<li>None identified</li>"}</ul>
    `),

    sec("8. Supporting material — why PASS or FAIL", `
      <p><strong>Verdict: ${r.supporting_explanation.verdict}</strong></p>
      <p style="margin:0.75rem 0;font-size:0.9rem">The black supporting material must form a <em>continuous, nearly circular ring</em> around the machined pore. Nodes (red circles) may be cut or destroyed — that is acceptable per project specification.</p>
      <h3>Why supporting material PASSES</h3>
      <ul class="reasons pass">${r.supporting_explanation.reasons_pass.map(x => `<li>${x}</li>`).join("") || "<li>No pass factors identified</li>"}</ul>
      <h3>Why supporting material FAILS</h3>
      <ul class="reasons fail">${r.supporting_explanation.reasons_fail.map(x => `<li>${x}</li>`).join("") || "<li>No failure factors identified</li>"}</ul>
    `),

    sec("9. Theory, project context & ML notes", `
      <div class="theory"><ul>${r.theory_notes.map(n => `<li>${n}</li>`).join("")}</ul></div>
      <p style="margin-top:1rem;font-size:0.88rem;color:#64748b">
        <strong>Phase 1</strong> (unknown position): find robust EDM settings for any landing point.<br/>
        <strong>Phase 2</strong> (known x,y): map circularity across the working area grid.<br/>
        Reference lab success: Run 4 at 4 A, 150 µs, 80 % with 900 µm tool and ~235.6 µm pore.
      </p>
    `),
  ].join("");
}
