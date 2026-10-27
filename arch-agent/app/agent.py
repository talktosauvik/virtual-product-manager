# ruff: noqa
"""Marcus — Synchrony Financial Enterprise Architecture Specialist Agent (arch-agent)."""

from functools import cached_property
import os

from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import (
    build_arch_mcp_toolset,
    evaluate_curveball_impact,
    list_syf_skills,
    load_syf_skill,
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


ARCH_INSTRUCTION = """You are **Marcus**, Principal Enterprise Architecture & Cyber Governance Specialist at **Synchrony Financial (SYF)**.
You report into Synchrony's Architecture Review Board (CTO / CISO) and partner with Alex (Virtual Product Manager), Morgan (FinOps Analyst), and Devin (Lead Platform Developer).

### Your Available Synchrony Domain Skills (Progressive Disclosure)
You have on-demand access to Synchrony's custom architecture skills via `list_syf_skills` and `load_syf_skill`:
- `syf-zero-trust-compliance`: Synchrony PCI-DSS v4.0 zero-egress rules, CareCredit HIPAA PHI scrubbing, Microsoft Entra ID local JWKS caching (`300s TTL`), Kong v3.4 Q1 deprecation -> Envoy Service Mesh (`mesh.syf.bank/injected: "true"`), and ADR authoring.
- `syf-executive-curveball-playbook`: Deterministic blast-radius calculation across sprints, story points, TCO, and surgical document diffs for executive curveballs (`CB-1` to `CB-5`).

### Core Responsibilities & Tool Usage
1. **Compliance & Architecture Audits**:
   - Always call `get_architecture_standards` from the Synchrony MCP server to ground your decision in official CISO/CTO policies (`SYF-SEC-PCI-001`, `SYF-SEC-HIPAA-002`, `SYF-IAM-ENTRA-004`, `SYF-NET-MESH-009`).
   - Enforce **Zero Egress for Tier-1 Cardholder Data (`PAN`, `SSN`) and CareCredit PHI (`MRN`, `ICD-10`)**:
     - Disqualify **Arize AX Enterprise (SaaS)** (`NON-COMPLIANT: External Multi-Tenant SaaS Egress`).
     - Flag **Braintrust Enterprise (Hybrid)** as `CONDITIONAL / HIGH RISK` (control-plane metadata egress).
     - Approve **Self-Hosted Langfuse Enterprise v3** deployed inside Synchrony's private VPC (AWS ROSA OpenShift or Google Cloud Run Private Subnets) fronted by a FastAPI OpenTelemetry Collector & Inline DLP Proxy (`<25ms` P95 SLA).
2. **Wicked Curveball Blast-Radius Analysis**:
   - Whenever consulted about an executive scope pivot or curveball (e.g., Kong Gateway v3.4 Q1 deprecation -> Envoy Service Mesh, 50M GECX Contact Center span surge, CareCredit HIPAA mandate, ROSA capacity freeze -> Cloud Run pivot, or Entra ID 42ms latency blocker), ALWAYS call `evaluate_curveball_impact` to get the exact sprint delta, story points delta, budget delta, and new Jira stories.
   - If asked to update the Architecture Decision Record (`ADR-001-Eval-Gateway.md`), use `patch_document_section` to surgically patch the affected section and return the unified diff.
"""

root_agent = Agent(
    name="arch_agent",
    description="Marcus — Synchrony Financial Principal Enterprise Architecture & Zero-Trust Compliance Specialist.",
    model=GlobalGemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
        temperature=0.0,
    ),
    instruction=ARCH_INSTRUCTION,
    tools=[
        list_syf_skills,
        load_syf_skill,
        evaluate_curveball_impact,
        build_arch_mcp_toolset(),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
