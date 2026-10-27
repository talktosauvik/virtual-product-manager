# ruff: noqa
"""Devin — Synchrony Financial Lead Platform Developer & SDLC Scaffolder Agent (dev-agent)."""

from functools import cached_property
import os

from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import (
    build_dev_mcp_toolset,
    list_syf_skills,
    load_syf_skill,
    scaffold_evaluation_gateway,
)

MODEL = os.environ.get("MODEL", "gemini-3.5-flash-lite")
THINKING_LEVEL = os.environ.get("THINKING_LEVEL", "LOW")


class GlobalGemini(Gemini):
    """Routes Gemini 3.x requests through the 'global' Vertex AI endpoint regardless of runtime region."""

    @cached_property
    def api_client(self) -> genai.Client:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "vertexai-l300-capstone")
        return genai.Client(
            vertexai=True,
            project=project,
            location="global",
            http_options=types.HttpOptions(
                headers=self._tracking_headers(),
                retry_options=self.retry_options,
            ),
        )


DEV_INSTRUCTION = """You are **Devin**, Lead Platform & AI Infrastructure Developer at **Synchrony Financial (SYF)**.
You work with Alex (Virtual Product Manager), Marcus (Enterprise Architect), and Morgan (FinOps Analyst) to scaffold hardened OpenShift (ROSA) and Cloud Run microservices and synchronize Bitbucket branches/PRs with Jira stories.

### Your Available Synchrony Domain Skills (Progressive Disclosure)
Use `list_syf_skills` and `load_syf_skill` to inspect Synchrony's engineering runbooks:
- `syf-rosa-gateway-scaffolding`: Hardened Red Hat UBI9 (`registry.access.redhat.com/ubi9/python-312:latest`, UID `1001`) Dockerfile templates, FastAPI OpenTelemetry W3C `traceparent` collector proxy, safe `json.dumps`/`json.loads` compiled regex PII/PAN/SSN/MRN scrubbing (strictly ZERO `eval()`), and Envoy Service Mesh (`mesh.syf.bank/injected: "true"`) Kubernetes manifests.
- `syf-sdlc-backlog-sync`: Bitbucket branch naming (`feature/AI-EVAL-101-...`), Pull Request creation, and Jira story linking.

### Core Workflow
1. When asked to scaffold the Evaluation & Observability Gateway microservice:
   - Call `scaffold_evaluation_gateway` to generate `Dockerfile`, `proxy_gateway.py`, `k8s_deployment.yaml`, and `requirements.txt` and upload them to `gs://vertexai-l300-capstone-syf-vpm-workspace/scaffolded_code/`.
   - Call `create_bitbucket_branch_and_pr` on the Synchrony MCP server to open the linked Bitbucket Pull Request against the Jira story (e.g. `AI-STORY-102`).
2. Always return the complete GCS URIs, Bitbucket PR URL, and key code snippets (`Dockerfile`, `sanitize_telemetry_payload` in `proxy_gateway.py`, and Envoy Service Mesh annotations in `k8s_deployment.yaml`).
"""

root_agent = Agent(
    name="dev_agent",
    description="Devin — Synchrony Financial Lead Platform Developer & OpenShift/FastAPI Code Scaffolder.",
    model=GlobalGemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
        temperature=0.0,
    ),
    instruction=DEV_INSTRUCTION,
    tools=[
        list_syf_skills,
        load_syf_skill,
        scaffold_evaluation_gateway,
        build_dev_mcp_toolset(),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
