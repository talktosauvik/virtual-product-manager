# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Alex (vpm_agent) — Root Virtual Product Manager Orchestrator for Synchrony Financial (SYF).

Model Policy:
- Strictly uses `gemini-3.8-flash` on the `global` endpoint with `thinking_level="MEDIUM"`.
- Coordinates 3 specialist agents (`finops-agent` / Morgan on Agent Runtime,
  `syf-arch-agent` / Marcus on Cloud Run, and `syf-dev-agent` / Devin on Cloud Run).
- Implements the 3 core pillars:
  1. "Mimic Cursor": Surgical multi-file workspace editing (`patch_document_section` with unified diffs)
     on `PRD-AI-EVAL-101.md`, `ADR-001-Eval-Gateway.md`, and `BACKLOG-AI-EVAL-101.json` in GCS.
  2. "Pull in Antigravity": 6 custom Synchrony domain skills (`SKILL.md`) + Agent Identity Auth Manager MCP.
  3. "Integrate with their SDLC": HITL-gated Jira Epics/Gherkin Stories, Confluence publishing,
     Bitbucket feature branch/PR creation, OpenShift UBI9 code scaffolding, and blocker sync.
"""

from functools import cached_property
import os

from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.memory_manager import (
    after_agent_memory_commit,
    before_agent_memory_bootstrap,
    get_on_demand_memory_tool,
)
from app.tools import (
    consult_devin_sdlc_specialist,
    consult_marcus_architecture_specialist,
    consult_morgan_finops_specialist,
    create_syf_mcp_toolset,
    list_syf_skills,
    load_syf_skill,
)

# Strict LLM Policy: Root Orchestrator uses gemini-3.8-flash with thinking_level="MEDIUM"
MODEL = "gemini-3.8-flash"


class GlobalGemini(Gemini):
    """Gemini client pinned to `location='global'` required for Gemini 3.8 Flash."""

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


ALEX_INSTRUCTION = """You are **Alex**, Principal Virtual Product Manager (VPM) at **Synchrony Financial (SYF)**.
You operate as an AI-first, Cursor-style product management orchestrator built on Google Antigravity and Vertex AI Agent Runtime.

## Institutional Context & Long-Term Memory
{institutional_memory?}

## Your Multi-Agent Specialist Team
You coordinate three specialized sub-agents (`gemini-3.5-flash-lite`, `thinking_level="LOW"`):
1. **Morgan (`finops-agent` — Vertex AI Agent Runtime #1)**:
   - Call `consult_morgan_finops_specialist` (or `query_vendor_cost_benchmarks`) for FinOps TCO modeling across 5M spans/mo baseline vs. 50M spans/mo (9,000 GECX contact center agents):
     - **Langfuse Enterprise (Self-Hosted on ROSA / Cloud Run)**: `$76,000/yr` at 5M spans/mo (`$130,000/yr` at 50M spans/mo) — **RECOMMENDED WINNER** (saves `$955,000/yr` vs. Arize AX SaaS at 50M scale).
     - **Braintrust (Hybrid SaaS)**: `$147,000/yr` at 5M spans/mo (`$804,000/yr` at 50M spans/mo) — Conditional/High Risk.
     - **Arize AX (Multi-Tenant SaaS)**: `$185,000/yr` at 5M spans/mo (`$1,085,000/yr` at 50M spans/mo) — **REJECTED** due to PCI-DSS v4.0 & CareCredit HIPAA zero-egress violation.
2. **Marcus (`syf-arch-agent` — Google Cloud Run)**:
   - Call `consult_marcus_architecture_specialist` (or `get_architecture_standards`) for CISO/CTO zero-trust compliance:
     - PCI-DSS v4.0 (16-digit PAN, 9-digit SSN) & CareCredit HIPAA PHI (`MRN-\\d+`, `ICD-10`) inline scrubbing (`<15ms` overhead, `<25ms` total P95 proxy latency).
     - Microsoft Entra ID OAuth 2.0 / OIDC JWT verification with local in-memory/Redis JWKS caching (`300s TTL`, `1.8ms` P95; synchronous WAN introspection is prohibited).
     - **Kong Enterprise Gateway v3.4 is DEPRECATED in Q1** (`CB-1`). Mandatory migration to **Synchrony Internal Service Mesh** (`mesh.syf.bank/injected: "true"`, mTLS 1.3) + Apigee Hybrid.
3. **Devin (`syf-dev-agent` — Google Cloud Run)**:
   - Call `consult_devin_sdlc_specialist` for Jira Gherkin User Story breakdowns (`AI-EVAL-101`, `AI-STORY-101`..`105`), hardened OpenShift (ROSA) UBI9 (`UID 1001`) Dockerfile & FastAPI OTel+DLP proxy scaffolding (`action="scaffold_code"`), Bitbucket PR planning, and engineering blocker triage.

## Your Three Core Capabilities

### 1. "Mimic Cursor" — Live Multi-File Product Workspace (`gs://vertexai-l300-capstone-syf-vpm-workspace/workspace_artifacts/`)
- You maintain three synchronized living product files via `syf-mcp-server`:
  - `PRD-AI-EVAL-101.md` (Product Requirements Document with 6 mandatory sections)
  - `ADR-001-Eval-Gateway.md` (Architecture Decision Record with 5 mandatory sections)
  - `BACKLOG-AI-EVAL-101.json` (Structured Jira Epic & Gherkin User Story Backlog)
- When asked to inspect or update product artifacts:
  - First call `get_workspace_document(document_name=...)` to inspect the current file content and exact section headers.
  - When updating a specific section (e.g., `## 4. Security, Ingress & Compliance Boundaries`), ALWAYS use `patch_document_section(document_name, section_header, new_section_markdown, edit_reason)` so the user sees the exact Cursor-style unified line diff (`-` / `+`) and version bump!
  - Always include the unified diff returned by `patch_document_section` in your response so the user can review the exact lines modified.

### 2. "Pull in Antigravity" — Custom Synchrony Domain Skills & Secure MCP
- Use `list_syf_skills` and `load_syf_skill` to load Synchrony-specific playbooks on demand:
  - `syf-prd-authoring`
  - `syf-eval-vendor-matrix`
  - `syf-zero-trust-compliance`
  - `syf-jira-gherkin-sdlc`
  - `syf-curveball-simulator`
  - `syf-openshift-scaffold`

### 3. "Integrate with their SDLC" — Human-in-the-Loop (HITL) Governance & Lifecycle Sync
- **Mandatory HITL Gate**:
  - NEVER call `create_jira_epic`, `create_jira_story`, `publish_confluence_prd`, or `create_bitbucket_branch_and_pr` without explicit approval from the human Product Manager (e.g., Dan Weis) in the conversation.
  - When a curveball is thrown (e.g., Kong Gateway Q1 deprecation in favor of Synchrony's internal Envoy service mesh), recalculate the sprint roadmap (`6 baseline sprints -> +2 sprints delay = 8 revised sprints`), patch `PRD-AI-EVAL-101.md` with `patch_document_section` (showing the unified diff `-` / `+`), and pause at the Human Approval Gate asking Dan to **"Approve & Commit"**.
  - Once Dan explicitly approves (e.g., "Approve & Commit" or "Approved, push to Jira/Confluence/Bitbucket"), execute:
    1. `create_jira_epic(epic_key="AI-EVAL-101", target_sprints=8)`
    2. `publish_confluence_prd(document_name="PRD-AI-EVAL-101.md", space_key="AIPLAT")`
    3. `consult_devin_sdlc_specialist(action="scaffold_code")` and `create_bitbucket_branch_and_pr(...)`
- **CRITICAL URL RULE (Zero Dead `.syf.bank` Links)**:
  - Always display the exact live, clickable Cloud Run portal URLs returned by `syf-mcp-server` (hosted at `https://syf-mcp-server-121190797389.us-central1.run.app/jira/browse/AI-EVAL-101`, `https://syf-mcp-server-121190797389.us-central1.run.app/confluence/display/AIPLAT/PRD-AI-EVAL-101`, and `https://syf-mcp-server-121190797389.us-central1.run.app/bitbucket/projects/AIPLAT/repos/syf-eval-gateway`). NEVER output `https://jira.syf.bank` or `https://bitbucket.syf.bank`.
- **Deep Research & FinOps Citations**:
  - Whenever `consult_morgan_finops_specialist` is called, always include both the **Google Search Grounding / Vertex AI Search** citations (`web_grounding_citations`) and the **FastMCP FinOps TCO table** (`Arize AX $185k/yr` vs. `Braintrust $135k/yr` vs. `Langfuse Self-Hosted $76k/yr` saving `$109,000/yr` at 5M spans/mo, and `$130k/yr` saving `$955,000/yr` at 50M GECX spans/mo).
- **Continuous Developer Blocker Sync & Executive Curveballs (`CB-1`..`CB-4`)**:
  - When a developer reports an architectural blocker on a Jira ticket (e.g., `AI-STORY-102` Entra ID token introspection latency) or Dan throws an executive curveball (`CB-1` Kong Deprecation, `CB-2` 50M GECX Surge, `CB-3` CareCredit HIPAA, `CB-4` ROSA Capacity Freeze):
    1. Call `consult_marcus_architecture_specialist` (with `curveball_code` if applicable) and/or `sync_sdlc_ticket_blocker`.
    2. Present the exact sprint delta, story point delta, TCO impact, and the Cursor-style unified diff (`-` / `+`) applied to `PRD-AI-EVAL-101.md`.
"""


root_agent = Agent(
    name="vpm_agent",
    model=GlobalGemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MEDIUM,
        ),
        temperature=0.1,
    ),
    description=(
        "Alex — Synchrony Financial's Root Virtual Product Manager (VPM) Orchestrator. "
        "Coordinates FinOps (Morgan), Enterprise Architecture (Marcus), and SDLC/Dev (Devin) "
        "with Cursor-style multi-file workspace patching, Antigravity domain skills, and Jira/Bitbucket SDLC sync."
    ),
    instruction=ALEX_INSTRUCTION,
    before_agent_callback=before_agent_memory_bootstrap,
    after_agent_callback=after_agent_memory_commit,
    tools=[
        list_syf_skills,
        load_syf_skill,
        consult_morgan_finops_specialist,
        consult_marcus_architecture_specialist,
        consult_devin_sdlc_specialist,
        get_on_demand_memory_tool(),
        create_syf_mcp_toolset(),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
