"""LLM engineering assistant for LatticeFlow EDM."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SYSTEM_PROMPT = """You are the LatticeFlow EDM Engineering Assistant — an expert in wire/pore EDM machining of lattice structures.

You help users understand:
- **Pores** (white circles): open gaps in the lattice; size = user pore diameter input.
- **Nodes** (red circles): fixed-size strut junctions (~235.6 µm); do NOT grow when pore diameter changes.
- **Struts** (black lines): supporting beams connecting nodes; must stay intact as a circular ring.
- **Tool circle**: EDM electrode footprint; purple dashed = full diameter, red = machined zone.
- **Circularity score** (1–5): predicted boundary roundness from ML trained on 16 SEM experiments.
- **PASS** requires score ≥ 3.5, ratio ≥ 0.70, and supporting material intact.

When analysis context is provided, use it precisely. Recommend the ML-suggested (x,y) when the user's position fails.
Be clear, educational, and concise. Use µm for microns. Reference lab success: Run 4 at 4 A, 150 µs, 80 %.
If no API key is configured, tell the user to add ANTHROPIC_API_KEY or OPENAI_API_KEY, or paste a key in chat settings."""


def _resolve_api_key(api_key: str | None) -> tuple[str, str]:
    """Return (key, provider) where provider is 'anthropic' or 'openai'."""
    key = (api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return "", ""
    if key.startswith("sk-ant-") or os.environ.get("ANTHROPIC_API_KEY"):
        return key, "anthropic"
    return key, "openai"


def build_analysis_context(payload: dict | None) -> str:
    if not payload:
        return "No analysis has been run yet in this session."

    rep = payload.get("report") or {}
    res = payload.get("results") or {}
    opt = rep.get("optimal_position") or {}
    u = rep.get("user_inputs") or {}

    lines = [
        "=== CURRENT USER ANALYSIS ===",
        f"EDM: {u.get('peak_current_A')} A, {u.get('pulse_on_us')} µs pulse-on, {u.get('duty_pct')} % duty",
        f"Geometry: tool {u.get('tool_diameter_um')} µm, pore {u.get('pore_diameter_um')} µm, area {u.get('working_area_um')} µm",
        f"User position: ({u.get('tool_x_um')}, {u.get('tool_y_um')}) µm",
        f"Valid X/Y range: [{u.get('valid_x_range', ['?', '?'])[0]}, {u.get('valid_x_range', ['?', '?'])[1]}] µm",
        f"Result: {res.get('pass_fail')} | score {res.get('circularity_1to5')}/5 | ratio {res.get('circularity_ratio')}",
        f"Supporting material: {'PASS' if res.get('supporting_material_ok') else 'FAIL'}",
        f"Tool/pore ratio: {res.get('tool_pore_ratio')}",
        f"Geometry risk: {res.get('geometry_risk')}",
        f"Strut intersection: {res.get('strut_intersection_um')} µm",
    ]

    if opt.get("recommended_x_um"):
        lines += [
            "=== ML RECOMMENDED POSITION (same EDM + geometry, only x,y changed) ===",
            f"Recommended: ({opt['recommended_x_um']}, {opt['recommended_y_um']}) µm",
            f"Predicted score: {opt.get('recommended_circularity_1to5')}/5 | {opt.get('recommended_pass_fail')}",
            f"Improvement vs current: +{opt.get('improvement_score', 0)} score points",
            f"Explanation: {opt.get('explanation', '')}",
            f"PASS position exists on grid: {opt.get('pass_position_exists')}",
        ]

    fail_reasons = (rep.get("circularity_explanation") or {}).get("reasons_fail", [])
    sup_fail = (rep.get("supporting_explanation") or {}).get("reasons_fail", [])
    if fail_reasons or sup_fail:
        lines.append("=== FAILURE REASONS ===")
        lines.extend(f"- {r}" for r in fail_reasons + sup_fail)

    return "\n".join(lines)


def _call_anthropic(key: str, system: str, history: list[dict], user_message: str) -> dict:
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    msgs = []
    for h in history[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": user_message})

    body = json.dumps({
        "model": model,
        "max_tokens": 1400,
        "system": system,
        "messages": msgs,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    reply = data["content"][0]["text"].strip()
    return {"reply": reply, "model": model, "provider": "anthropic"}


def _call_openai(key: str, messages: list[dict]) -> dict:
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 1400,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    reply = data["choices"][0]["message"]["content"].strip()
    return {"reply": reply, "model": model, "provider": "openai"}


def chat_completion(
    user_message: str,
    history: list[dict],
    analysis_payload: dict | None,
    api_key: str | None = None,
) -> dict:
    key, provider = _resolve_api_key(api_key)
    if not key:
        return {
            "reply": (
                "No API key configured. Paste your Anthropic key (sk-ant-...) or OpenAI key (sk-...) "
                "in the chat gear icon, or set ANTHROPIC_API_KEY in a .env file. "
                "Run Analyze first, then ask about your results."
            ),
            "error": "missing_api_key",
        }

    context = build_analysis_context(analysis_payload)
    system = SYSTEM_PROMPT + "\n\n" + context

    try:
        if provider == "anthropic" or key.startswith("sk-ant-"):
            return _call_anthropic(key, system, history, user_message)
        messages = [{"role": "system", "content": system}]
        for h in history[-10:]:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})
        return _call_openai(key, messages)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_body)
            detail = (
                parsed.get("error", {}).get("message")
                or parsed.get("message")
                or err_body[:300]
            )
        except json.JSONDecodeError:
            detail = err_body[:300]
        return {"reply": f"API error ({e.code}): {detail}", "error": "api_error"}
    except Exception as e:
        return {"reply": f"Could not reach LLM API: {e}", "error": "network_error"}
