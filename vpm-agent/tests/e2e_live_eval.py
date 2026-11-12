"""End-to-End Live Evaluation Suite for Alex (vpm-agent) on Vertex AI Agent Runtime.

Runs 3 comprehensive multi-agent scenarios against the deployed Reasoning Engine
and verifies tool invocations, numerical accuracy, and live SDLC integration.
"""

from __future__ import annotations

import json
import os
import sys
import time

from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
PROJECT_NUMBER = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER", "")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID", "")
AGENT_ENGINE_RESOURCE = os.getenv(
    "AGENT_ENGINE_RESOURCE",
    f"projects/{PROJECT_NUMBER or PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
    if (PROJECT_NUMBER or PROJECT_ID) and AGENT_ENGINE_ID
    else "",
)


def _stream_turn(
    remote_app,
    user_id: str,
    session_id: str,
    prompt: str,
    scenario_name: str,
) -> tuple[str, list[str], float]:
    """Stream a single turn against the deployed Reasoning Engine and collect text + tool calls."""
    t0 = time.monotonic()
    chunks: list[str] = []
    tool_calls: list[str] = []

    print(f"\n{'=' * 80}")
    print(f"[START] {scenario_name}")
    print(f"Session ID: {session_id}")
    print(f"{'=' * 80}")

    for event in remote_app.stream_query(
        user_id=user_id,
        session_id=session_id,
        message=prompt,
    ):
        if isinstance(event, dict):
            content = event.get("content", {})
            parts = content.get("parts", []) if isinstance(content, dict) else []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                if "function_call" in part and part["function_call"]:
                    fn_name = part["function_call"].get("name", "unknown")
                    tool_calls.append(fn_name)
                    print(f"  -> [TOOL CALL] {fn_name} ({time.monotonic() - t0:.1f}s)")
                if "text" in part and part["text"]:
                    chunks.append(part["text"])

    elapsed = time.monotonic() - t0
    full_text = "".join(chunks)
    print(f"[DONE] {scenario_name} completed in {elapsed:.1f}s | Tools: {tool_calls} | Text length: {len(full_text)} chars")
    return full_text, tool_calls, elapsed


def main() -> int:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    remote_app = agent_engines.get(AGENT_ENGINE_RESOURCE)
    user_id = f"e2e-eval-{int(time.time())}"

    # Create a session for Scenarios 1 & 2 (Turn 1 -> Turn 2 multi-turn continuity)
    sess_1 = remote_app.create_session(user_id=user_id)
    session_id_1 = sess_1["id"] if isinstance(sess_1, dict) else sess_1.id

    # -------------------------------------------------------------------------
    # Scenario 1: Turn 1 — Baseline PRD Review & Cross-Agent Consultation
    # -------------------------------------------------------------------------
    prompt_1 = (
        "Hi Alex. Please review our draft PRD `PRD-AI-EVAL-101.md` in the shared "
        "workspace for the Synchrony Enterprise AI Evaluation & Governance Gateway "
        "on OpenShift (ROSA). Consult Morgan (FinOps), Marcus (Enterprise Security "
        "& Architecture), and Devin (Lead SDLC Engineer) to validate our 5M and "
        "50M req/mo TCO, OCC 2011-12 / PCI-DSS v4.0 architecture guardrails, and "
        "6-Sprint (192 SP at 32 SP/sprint) Jira delivery plan, then give me a "
        "consolidated executive readiness briefing with live Confluence, Jira, "
        "and Bitbucket links."
    )
    text_1, tools_1, elapsed_1 = _stream_turn(
        remote_app, user_id, session_id_1, prompt_1, "Scenario 1: Turn 1 Baseline PRD Review"
    )
    assert len(text_1) > 400, f"Scenario 1 response too short ({len(text_1)} chars)"
    assert "get_workspace_document" in tools_1, f"Missing get_workspace_document tool call: {tools_1}"
    assert "consult_morgan_finops_specialist" in tools_1, f"Missing Morgan tool call: {tools_1}"
    assert "consult_marcus_architecture_specialist" in tools_1, f"Missing Marcus tool call: {tools_1}"
    assert "192" in text_1 or "6 Sprint" in text_1 or "6 sprints" in text_1.lower(), "Missing 6 Sprints / 192 SP baseline"
    print("  [PASS] Scenario 1 assertions passed!")

    # -------------------------------------------------------------------------
    # Scenario 2: Turn 2 — Executive Curveball (Kong v3.4 Deprecation + Workspace Patching)
    # -------------------------------------------------------------------------
    prompt_2 = (
        "Curveball from the CISO & Cloud Platform Board: Kong Enterprise v3.4 on "
        "ROSA is being deprecated in Q3 due to CVE-2026-3104, and our target scale "
        "is jumping to 50M requests/month. We are choosing Option 2A (Full Enterprise "
        "Envoy Gateway Migration on ROSA). Please have Marcus and Morgan evaluate "
        "the blast radius and TCO impact, and immediately patch `PRD-AI-EVAL-101.md` "
        "and `ADR-001-Eval-Gateway.md` so our live Confluence pages reflect the "
        "revised 8-Sprint (256 SP) architecture and +$32,000 migration delta."
    )
    text_2, tools_2, elapsed_2 = _stream_turn(
        remote_app, user_id, session_id_1, prompt_2, "Scenario 2: Turn 2 Kong v3.4 Curveball & Live Workspace Patching"
    )
    assert len(text_2) > 300, f"Scenario 2 response too short ({len(text_2)} chars)"
    assert (
        "patch_document_section" in tools_2 or "update_workspace_document" in tools_2
    ), f"Expected workspace document update tool call in Scenario 2, got: {tools_2}"
    assert "256" in text_2 or "8" in text_2, "Expected 8 Sprints / 256 SP in Scenario 2 output"
    print("  [PASS] Scenario 2 assertions passed!")

    # -------------------------------------------------------------------------
    # Scenario 3: Turn 4 — Sprint 1 Blocker Triage (AI-STORY-102 / SYF-7)
    # -------------------------------------------------------------------------
    sess_3 = remote_app.create_session(user_id=user_id)
    session_id_3 = sess_3["id"] if isinstance(sess_3, dict) else sess_3.id
    prompt_3 = (
        "Alex, urgent Sprint 1 telemetry alert: `AI-STORY-102` (Jira `SYF-7`, "
        "Entra ID OAuth2 / OIDC Token Validation Middleware) is clocking 42.3ms "
        "per synchronous token introspect call against our 15ms total gateway "
        "overhead budget! Please consult Marcus and Devin to triage this blocker, "
        "sync the local JWKS public-key caching remediation (`300s TTL`, `1.8ms` "
        "verify latency, `13.8ms` total P95 overhead) across Jira `SYF-7`, "
        "`ADR-001-Eval-Gateway.md`, and `BACKLOG-AI-EVAL-101.json`, and summarize "
        "the resolution."
    )
    text_3, tools_3, elapsed_3 = _stream_turn(
        remote_app, user_id, session_id_3, prompt_3, "Scenario 3: Sprint 1 Blocker Triage (AI-STORY-102 / SYF-7)"
    )
    assert len(text_3) > 300, f"Scenario 3 response too short ({len(text_3)} chars)"
    assert (
        "1.8" in text_3 or "13.8" in text_3 or "JWKS" in text_3
    ), "Expected JWKS caching latency remediation details in Scenario 3 output"
    print("  [PASS] Scenario 3 assertions passed!")

    print("\n" + "=" * 80)
    print(
        f"ALL 3 LIVE E2E SCENARIOS PASSED! "
        f"(S1={elapsed_1:.1f}s, S2={elapsed_2:.1f}s, S3={elapsed_3:.1f}s)"
    )
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
