let lastReport = null;
let lastResults = null;
let lastLatticeImg = null;
let lastBounds = null;

const TOOL_DIAMETER_OPTIONS = [400,500,600,700,800,900,1000,1100,1200,1300,1400,1500];

function initToolDiameterSelect() {
  const sel = document.getElementById("tool_diameter");
  if (!sel) return;
  if (sel.querySelectorAll("option[value]:not([value=''])").length >= 12) return;
  const ph = document.createElement("option");
  ph.value = ""; ph.disabled = true; ph.selected = true; ph.textContent = "Choose size";
  sel.innerHTML = "";
  sel.appendChild(ph);
  TOOL_DIAMETER_OPTIONS.forEach(d => {
    const o = document.createElement("option");
    o.value = String(d); o.textContent = `${d} µm`;
    sel.appendChild(o);
  });
}

function payload() {
  return {
    peak_current: parseFloat(document.getElementById("peak_current").value),
    pulse_on: parseFloat(document.getElementById("pulse_on").value),
    duty: parseFloat(document.getElementById("duty").value),
    tool_diameter: parseFloat(document.getElementById("tool_diameter").value),
    pore_diameter: parseFloat(document.getElementById("pore_diameter").value),
    working_area: parseFloat(document.getElementById("working_area").value),
    tool_x: parseFloat(document.getElementById("tool_x").value),
    tool_y: parseFloat(document.getElementById("tool_y").value),
  };
}

function showError(msg) {
  const el = document.getElementById("error");
  el.textContent = msg;
  el.classList.remove("hidden");
}
function hideError() { document.getElementById("error").classList.add("hidden"); }

async function updateBounds() {
  const td = document.getElementById("tool_diameter").value;
  const pd = document.getElementById("pore_diameter").value;
  const wa = document.getElementById("working_area").value;
  if (!td || !pd || !wa) {
    ["live-radius","live-ratio","live-x","live-y"].forEach(id => {
      document.getElementById(id).textContent = "—";
    });
    return;
  }
  try {
    const res = await fetch("/api/bounds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_diameter: +td, pore_diameter: +pd, working_area: +wa }),
    });
    const d = await res.json();
    if (!res.ok) return;
    lastBounds = d;
    const r = d.tool_radius;
    document.getElementById("live-radius").textContent = `${r.toFixed(0)} µm`;
    document.getElementById("live-ratio").textContent = d.tool_pore_ratio;
    document.getElementById("live-x").textContent = `${d.x_min}–${d.x_max} µm`;
    document.getElementById("live-y").textContent = `${d.y_min}–${d.y_max} µm`;
    document.getElementById("live-formula").textContent =
      `Valid: [${d.x_min}, ${d.x_max}] µm  (radius ${r.toFixed(0)} µm, area ${wa} µm)`;
    document.getElementById("position-hint").textContent =
      `Place tool center between ${d.x_min} and ${d.x_max} µm`;
    document.getElementById("tool_x").placeholder = `${d.x_min} – ${d.x_max}`;
    document.getElementById("tool_y").placeholder = `${d.y_min} – ${d.y_max}`;
  } catch (_) {}
}

["tool_diameter", "pore_diameter", "working_area"].forEach(id => {
  const el = document.getElementById(id);
  el.addEventListener("change", updateBounds);
  el.addEventListener("input", updateBounds);
});

function setGauge(ratio, pass) {
  const ring = document.getElementById("gauge-ring");
  const val = document.getElementById("gauge-val");
  if (!ring) return;
  const pct = Math.min(1, Math.max(0, ratio));
  ring.style.strokeDashoffset = 327 * (1 - pct);
  ring.style.stroke = pass ? "#059669" : ratio >= 0.5 ? "#d97706" : "#dc2626";
  val.textContent = ratio.toFixed(2);
}

function statCard(val, lbl, cls = "") {
  return `<div class="stat ${cls}"><div class="val">${val}</div><div class="lbl">${lbl}</div></div>`;
}

function renderOptimalHint(rep) {
  const el = document.getElementById("optimal-hint");
  const o = rep?.optimal_position;
  if (!el || !o?.recommended_x_um) {
    if (el) el.classList.add("hidden");
    return;
  }

  const recPass = o.recommended_pass_fail === "PASS";
  const improved = o.improvement_score > 0;
  el.classList.remove("hidden");
  el.innerHTML = `
    <h4>Recommended position (ML grid scan)</h4>
    <p>${o.explanation}</p>
    <div class="optimal-coords">
      <span><strong>X = ${o.recommended_x_um}</strong> µm</span>
      <span><strong>Y = ${o.recommended_y_um}</strong> µm</span>
      <span>Score <strong>${o.recommended_circularity_1to5}</strong>/5</span>
      <span class="${recPass ? "pass" : ""}">${o.recommended_pass_fail}</span>
    </div>
    ${!o.same_as_current && improved ? `
      <button type="button" class="btn btn-apply-pos" id="btn-apply-pos">
        Apply recommended position
      </button>` : ""}
    <p class="note">Full details in Engineering Report → Section 4</p>
  `;

  const applyBtn = document.getElementById("btn-apply-pos");
  if (applyBtn) {
    applyBtn.addEventListener("click", () => {
      document.getElementById("tool_x").value = o.recommended_x_um;
      document.getElementById("tool_y").value = o.recommended_y_um;
      applyBtn.textContent = "Applied — click Analyze to verify";
    }, { once: true });
  }
}

function renderMetrics(r, rep) {
  const pass = r.pass_fail === "PASS";

  document.getElementById("results-empty").classList.add("hidden");
  document.getElementById("results").classList.remove("hidden");

  const banner = document.getElementById("verdict-banner");
  banner.className = `verdict-bar ${pass ? "pass" : "fail"}`;
  banner.textContent = pass
    ? "PASS — Circular supporting boundary expected"
    : "FAIL — See recommended position below or Engineering Report";

  setGauge(r.circularity_ratio, pass);

  document.getElementById("metrics").innerHTML = [
    statCard(r.pass_fail, "Overall", pass ? "pass" : "fail"),
    statCard(r.circularity_1to5, "Score /5"),
    statCard(r.circularity_ratio, "Ratio"),
    statCard(r.supporting_material_ok ? "PASS" : "FAIL", "Supporting", r.supporting_material_ok ? "pass" : "fail"),
    statCard(r.geometry_risk, "Geo risk"),
    statCard(r.tool_pore_ratio, "Tool/pore"),
  ].join("");

  const ce = rep.circularity_explanation;
  const se = rep.supporting_explanation;
  const pc = rep.pass_criteria;

  document.getElementById("verdict-box").innerHTML = `
    <h4>Analysis summary</h4>
    <div class="criteria-box">
      <strong>Pass requires:</strong> Score ≥ ${pc.circularity_score_min}/5 · Ratio ≥ ${pc.circularity_ratio_min} · Supporting intact
    </div>
    <p class="viz-note"><strong>Preview legend:</strong> White circles = pores (grow with pore diameter). Red circles = nodes (fixed ~235.6 µm). Black lines = struts.</p>
    <h4>Circularity</h4>
    <ul>${[...ce.reasons_pass.map(t => `<li class="pass">${t}</li>`), ...ce.reasons_fail.map(t => `<li class="fail">${t}</li>`)].join("")}</ul>
    <h4>Supporting material — ${r.supporting_material_ok ? "PASS" : "FAIL"}</h4>
    <ul>${[...se.reasons_pass.map(t => `<li class="pass">${t}</li>`), ...se.reasons_fail.map(t => `<li class="fail">${t}</li>`)].join("")}</ul>
    <p class="note">Nodes may be destroyed. Black supporting ring must remain continuous.</p>
  `;

  renderOptimalHint(rep);
}

document.getElementById("analyze-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();
  const btn = document.getElementById("btn-run");
  btn.disabled = true;
  btn.querySelector(".btn-text").classList.add("hidden");
  btn.querySelector(".spinner").classList.remove("hidden");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    const data = await res.json();
    if (!res.ok) { showError(data.error); return; }

    lastReport = data.report;
    lastResults = data.results;
    lastLatticeImg = data.lattice_image;
    window.lastReport = lastReport;
    window.lastResults = lastResults;
    document.getElementById("lattice-img").src = "data:image/png;base64," + data.lattice_image;
    renderMetrics(data.results, data.report);
  } catch {
    showError("Server not running. Double-click RUN_SITE.bat, then open http://localhost:5050");
  } finally {
    btn.disabled = false;
    btn.querySelector(".btn-text").classList.remove("hidden");
    btn.querySelector(".spinner").classList.add("hidden");
  }
});

document.getElementById("btn-report").addEventListener("click", () => {
  if (!lastReport) return;
  sessionStorage.setItem("latticeReport", JSON.stringify({ report: lastReport, image: lastLatticeImg, bounds: lastBounds }));
  window.open("/report", "_blank", "width=1024,height=920,scrollbars=yes");
});

document.getElementById("btn-grid").addEventListener("click", async () => {
  hideError();
  const p = payload();
  if ([p.peak_current, p.pulse_on, p.duty, p.tool_diameter, p.pore_diameter, p.working_area].some(isNaN)) {
    showError("Fill all fields before grid scan.");
    return;
  }
  const btn = document.getElementById("btn-grid");
  btn.disabled = true;
  btn.textContent = "Scanning…";
  try {
    const res = await fetch("/api/grid-scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...p, grid_step: 75 }),
    });
    const data = await res.json();
    if (!res.ok) { showError(data.error); return; }
    document.getElementById("grid-results").classList.remove("hidden");
    document.getElementById("grid-metrics").innerHTML = [
      statCard(data.best_circularity.toFixed(2), "Best score"),
      statCard(`(${data.best_position.x.toFixed(0)}, ${data.best_position.y.toFixed(0)})`, "Best position"),
      statCard(data.pass_count, "PASS points", "pass"),
      statCard(data.total_points, "Grid points"),
    ].join("");
    document.getElementById("heatmap-img").src = "data:image/png;base64," + data.heatmap_image;
    document.getElementById("best-img").src = "data:image/png;base64," + data.best_lattice_image;
  } catch { showError("Grid scan failed."); }
  btn.disabled = false;
  btn.textContent = "Grid scan";
});

updateBounds();
initToolDiameterSelect();
