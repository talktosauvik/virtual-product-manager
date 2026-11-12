"""Comprehensive unit tests for Alex (vpm-agent) tools, GCS/MCP fallback resilience, and Agile math."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from app import tools


def test_load_gcs_json_never_raises_on_unauthorized_or_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _load_gcs_json never crashes with 401/network errors and falls back to local seed_data."""
    monkeypatch.setattr(tools, "SYF_MCP_SERVER_URL", "http://127.0.0.1:1/mcp")
    monkeypatch.setattr(tools, "WORKSPACE_BUCKET", "non-existent-unit-test-bucket")
    backlog = tools._load_gcs_json("workspace_artifacts/BACKLOG-AI-EVAL-101.json")
    assert backlog.get("epic_key") == "AI-EVAL-101"
    assert backlog.get("jira_epic_key") == "SYF-5"
    assert backlog.get("status") == "DRAFT"

    standards = tools._load_gcs_json("seed_data/architecture_standards.json")
    assert standards.get("organization") == "Synchrony Financial (SYF)"
    assert "baseline_policies" in standards

    benchmarks = tools._load_gcs_json("seed_data/eval_vendor_benchmarks.json")
    assert "arize_ax" in benchmarks.get("vendors", {})
    assert "langfuse" in benchmarks.get("vendors", {})


@pytest.mark.asyncio
async def test_consult_morgan_finops_specialist_tco_math() -> None:
    """Verify Morgan returns exact 5M and 50M TCO numbers and deep research citations."""
    with patch.object(
        tools,
        "_run_live_google_search_grounding",
        return_value={
            "tool_used": "Google Search Grounding",
            "live_research_summary": "Langfuse v3 uses ClickHouse.",
            "web_grounding_citations": [{"title": "Langfuse Docs", "uri": "https://langfuse.com/docs"}],
        },
    ):
        res = await tools.consult_morgan_finops_specialist(
            research_question="Compare Arize AX, Braintrust, and Langfuse v3",
            monthly_spans_millions=5.0,
            include_gecx_50m_surge=True,
        )
    assert res["baseline_analysis"]["vendors"]["arize_ax"]["annual_tco_usd"] == 185000.0
    assert res["baseline_analysis"]["vendors"]["braintrust"]["annual_tco_usd"] == 135000.0
    assert res["baseline_analysis"]["vendors"]["langfuse"]["annual_tco_usd"] == 76000.0
    assert res["baseline_analysis"]["net_annual_savings_langfuse_vs_arize_usd"] == 109000.0
    assert res["gecx_50m_surge_projection"]["vendors"]["arize_ax"]["annual_tco_usd"] == 1085000.0
    assert res["gecx_50m_surge_projection"]["vendors"]["langfuse"]["annual_tco_usd"] == 130000.0
    assert res["gecx_50m_surge_projection"]["net_annual_savings_langfuse_vs_arize_usd"] == 955000.0


@pytest.mark.asyncio
async def test_consult_marcus_baseline_and_curveballs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Marcus Turn 1 baseline audit (3 categories) and Turn 2A/2B Agile velocity math."""
    monkeypatch.setattr(tools, "SYF_MCP_SERVER_URL", "http://127.0.0.1:1/mcp")
    monkeypatch.setattr(tools, "WORKSPACE_BUCKET", "non-existent-unit-test-bucket")
    # Turn 1: Baseline v1.0 review
    base_res = await tools.consult_marcus_architecture_specialist(
        architecture_proposal="Baseline v1.0 PRD-AI-EVAL-101 review",
        curveball_code="",
    )
    assert base_res["review_mode"] == "BASELINE_V1_ZERO_TRUST_AUDIT"
    assert len(base_res["baseline_audit_categories"]) == 3

    # Turn 2A: Kong Enterprise v3.4 Q1 Deprecation -> +32 SP (+1 Sprint, 6 -> 7 Sprints, +$16,000)
    with patch.object(
        tools,
        "_fetch_parallel_community_citations",
        return_value={
            "search_keywords": "Kong Envoy mTLS",
            "stackoverflow_api_hits": [{"title": "Envoy mTLS", "url": "https://stackoverflow.com/q/1"}],
            "github_issues_api_hits": [],
            "reddit_json_api_hits": [],
            "google_search_grounding": {"web_grounding_citations": []},
        },
    ):
        cb1_res = await tools.consult_marcus_architecture_specialist(
            architecture_proposal="Leadership announced Q1 deprecation of Kong Enterprise Gateway v3.4 -> Envoy Service Mesh",
            curveball_code="CB-1",
        )
    assert cb1_res["review_mode"] == "EXECUTIVE_CURVEBALL_IMPACT_ANALYSIS"
    math_2a = cb1_res["curveball_impact"]["agile_velocity_math"]
    assert math_2a["story_points_delta"] == 32
    assert math_2a["sprint_delta"] == 1
    assert math_2a["revised_sprints"] == 7
    assert math_2a["revised_story_points"] == 224
    assert math_2a["one_time_engineering_cost_delta_usd"] == 16000

    # Turn 2B: OpenTelemetry Python gRPC Memory Leak -> +32 SP (+1 Sprint, 6 -> 7 Sprints, +$16,000)
    with patch.object(
        tools,
        "_fetch_parallel_community_citations",
        return_value={
            "search_keywords": "OpenTelemetry Python gRPC memory",
            "stackoverflow_api_hits": [{"title": "OTel gRPC memory", "url": "https://stackoverflow.com/q/2"}],
            "github_issues_api_hits": [{"title": "Issue 123", "url": "https://github.com/open-telemetry/opentelemetry-python/issues/1"}],
            "reddit_json_api_hits": [{"title": "Reddit thread", "url": "https://www.reddit.com/r/devops/1"}],
            "google_search_grounding": {"web_grounding_citations": []},
        },
    ):
        cb2_res = await tools.consult_marcus_architecture_specialist(
            architecture_proposal="OpenTelemetry Python SDK gRPC BatchSpanProcessor memory leak above 5,000 req/sec -> switch to HTTP/protobuf",
            curveball_code="CB-DYNAMIC",
        )
    math_2b = cb2_res["curveball_impact"]["agile_velocity_math"]
    assert math_2b["story_points_delta"] == 32
    assert math_2b["sprint_delta"] == 1
    assert math_2b["revised_sprints"] == 7
    assert math_2b["revised_story_points"] == 224
    assert math_2b["one_time_engineering_cost_delta_usd"] == 16000


@pytest.mark.asyncio
async def test_consult_devin_sdlc_hitl_and_scaffold() -> None:
    """Verify Devin enforces HITL approval gate and generates compliant OpenShift UBI9 scaffold."""
    blocked = await tools.consult_devin_sdlc_specialist(action="execute_sdlc", human_approved=False)
    assert blocked["status"] == "HITL_APPROVAL_REQUIRED"

    approved = await tools.consult_devin_sdlc_specialist(action="execute_sdlc", human_approved=True)
    assert approved["status"] == "READY_FOR_MCP_EXECUTION"

    scaffold = await tools.consult_devin_sdlc_specialist(action="scaffold_code")
    assert "registry.access.redhat.com/ubi9/python-312" in scaffold["openshift_ubi9_dockerfile"]
    assert "USER 1001" in scaffold["openshift_ubi9_dockerfile"]
    assert "eval(" not in scaffold["fastapi_otel_dlp_proxy_py"]


@pytest.mark.asyncio
async def test_parallel_tool_execution() -> None:
    """Verify Morgan, Marcus, and Devin async tools execute concurrently via asyncio.gather."""
    with patch.object(
        tools,
        "_run_live_google_search_grounding",
        return_value={"tool_used": "mock", "live_research_summary": "ok", "web_grounding_citations": []},
    ):
        r_morgan, r_marcus, r_devin = await asyncio.gather(
            tools.consult_morgan_finops_specialist("TCO check"),
            tools.consult_marcus_architecture_specialist("Baseline check"),
            tools.consult_devin_sdlc_specialist(action="preview"),
        )
    assert r_morgan["baseline_analysis"]["vendors"]["langfuse"]["annual_tco_usd"] == 76000.0
    assert r_marcus["review_mode"] == "BASELINE_V1_ZERO_TRUST_AUDIT"
    assert r_devin["status"] == "PREVIEW_GENERATED"


def test_syf_mcp_server_tools_and_auth_manager_fast_path() -> None:
    """Verify syf-mcp-server tools and live_sdlc_client fast REST fallback."""
    import sys
    from pathlib import Path

    mcp_dir = str(Path(__file__).resolve().parents[3] / "syf-mcp-server")
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)

    import server as mcp_server  # type: ignore

    bench = mcp_server.query_vendor_cost_benchmarks(monthly_spans_millions=5.0, include_gecx_50m_projection=True)
    assert bench["requested_volume_analysis"]["vendors"]["langfuse"]["total_annual_tco_usd"] == 76000.0
    assert bench["gecx_50m_surge_projection"]["vendors"]["langfuse"]["total_annual_tco_usd"] == 130000.0
    standards = mcp_server.get_architecture_standards("all")
    assert standards.get("organization") == "Synchrony Financial (SYF)"


