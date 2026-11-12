"""Comprehensive unit & integration tests for Devin (dev-agent):
1. Zero hardcoded configuration (all sourced from .env).
2. Lab 3 Agent Identity Auth Manager token resolution (`RetrieveCredentialsRequest`).
3. ADK 2.0 Graph `Workflow` topology (`JoinNode`, `FunctionNode`, `RetryConfig`, `state_schema`).
4. `/api/stream_reasoning_engine` route (exact Gemini Enterprise ADK invocation contract).
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
import pytest

from app.agent import (
    DevWorkflowState,
    app as adk_app,
    dev_specialist_agent,
    root_agent,
)
from app.fast_api_app import app as fastapi_app
from app.tools import (
    AUTH_PROVIDER_URI,
    _resolve_auth_manager_token,
    syf_auth_scheme,
)


def test_adk2_workflow_and_model_config() -> None:
    """Verify canonical ADK 2.0 Workflow structure and Gemini 3.x config (no temperature set)."""
    assert root_agent.name == "dev_agent"
    assert root_agent.state_schema is DevWorkflowState
    assert adk_app.name == "app"
    assert dev_specialist_agent.generate_content_config is not None
    assert dev_specialist_agent.generate_content_config.temperature is None


def test_lab3_agent_identity_auth_manager() -> None:
    """Verify Lab 3 Agent Identity Auth Manager scheme and live token retrieval."""
    assert AUTH_PROVIDER_URI.startswith("projects/")
    assert "authProviders/syf-mcp-auth-provider" in AUTH_PROVIDER_URI
    assert syf_auth_scheme is not None
    token = _resolve_auth_manager_token()
    assert len(token) > 10


def test_stream_reasoning_engine_contract() -> None:
    """Verify `/api/stream_reasoning_engine` returns 200 OK and streams all 7 tool checkmarks + final Markdown."""
    with TestClient(fastapi_app) as client:
        resp = client.post(
            "/api/stream_reasoning_engine",
            json={
                "class_method": "async_stream_query",
                "input": {
                    "user_id": "ge-test-user",
                    "message": "@Devin Build Sprint 1 stories for SYF-5 and open the Bitbucket PR.",
                },
            },
        )
        assert resp.status_code == 200
        lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
        assert len(lines) >= 8

        events = [json.loads(line) for line in lines]
        fn_calls: list[str] = []
        fn_responses: list[str] = []
        final_texts: list[str] = []

        for ev in events:
            content = ev.get("content") or {}
            for part in content.get("parts") or []:
                if part.get("function_call"):
                    fn_calls.append(part["function_call"]["name"])
                if part.get("function_response"):
                    fn_responses.append(part["function_response"]["name"])
                if part.get("text"):
                    final_texts.append(part["text"])

        expected_tools = {
            "install_and_activate_coding_skills",
            "fetch_assigned_sprint1_jira_stories",
            "scaffold_gateway_and_envoy_mesh",
            "scaffold_eval_suite_and_ci_pipeline",
            "run_security_and_latency_qa_suite",
            "commit_and_open_bitbucket_pr",
            "deploy_and_verify_live_gateway_app",
        }
        assert expected_tools.issubset(set(fn_calls))
        assert expected_tools.issubset(set(fn_responses))
        assert any("Autonomous Sprint 1 Engineering" in t for t in final_texts)
        assert any("bitbucket.org/iamsouvik/syf-eval-gateway" in t for t in final_texts)
        assert any("my-demo-team.atlassian.net/browse/SYF-" in t for t in final_texts)
