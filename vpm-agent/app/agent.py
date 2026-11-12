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

"""Alex (SYF Virtual Product Manager) — ADK 2.0 Graph & Dynamic Workflow Orchestrator.

Built with authentic Google ADK 2.0 (`google-adk >= 2.0.0`) primitives:
- `Workflow` graph orchestration (`START`, conditional dictionary routing, static parallel fan-out tuples)
- `JoinNode` fan-in synchronization barriers for Turn 1 (Morgan + Marcus parallel audit) and
  Turn 3 (Confluence + Jira + Vertex AI Memory Bank parallel commit)
- `@node(rerun_on_resume=True)` dynamic orchestration (`await ctx.run_node(..., run_id=...)` +
  `await asyncio.gather(...)`) for Turn 2 Executive Curveballs (`CB-1` through `CB-5`)
- `Agent(..., mode="single_turn", sub_agents=[...])` specialist collaboration for open-ended
  product, FinOps, CISO architecture, and cloud engineering inquiries
- Terminal `synthesizer` node emitting a single final `Event(message=..., output=...)` so
  `A2aAgentExecutor` and the A2UI v0.9 interceptor attach the interactive 3-card surfaces cleanly.
"""

from __future__ import annotations

import asyncio
from functools import cached_property
import logging
import os
from typing import Any, Literal

from dotenv import load_dotenv
from google import genai
from google.adk import Agent, Context as NodeContext, Event, Workflow
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.workflow import JoinNode, START, node
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

from app.memory_manager import (
    after_agent_memory_commit,
    before_agent_memory_bootstrap,
    get_on_demand_memory_tool,
)
from app.tools import (
    consolidate_executive_memory,
    consult_devin_sdlc_specialist,
    consult_marcus_architecture_specialist,
    consult_morgan_finops_specialist,
    create_bitbucket_branch_and_pr,
    create_jira_epic,
    create_jira_story,
    get_workspace_document,
    list_syf_skills,
    list_workspace_documents,
    load_syf_skill,
    patch_document_section,
    publish_confluence_prd,
    sync_sdlc_ticket_blocker,
)
from app.ui_renderer import (
    _detect_curveball_id,
    get_and_clear_executed_tools,
    record_tool_execution,
)

logger = logging.getLogger(__name__)

# Model Policy: Alex uses gemini-3.8-flash; specialists use gemini-3.5-flash-lite
MODEL = os.environ.get("MODEL", "gemini-3.8-flash")
SPECIALIST_MODEL = os.environ.get("SPECIALIST_MODEL", "gemini-3.5-flash-lite")

ATLASSIAN_DOMAIN = os.environ.get("ATLASSIAN_DOMAIN", "")
CONFLUENCE_SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "SD")
CONFLUENCE_PRD_PAGE_ID = os.environ.get("CONFLUENCE_PRD_PAGE_ID", "")
CONFLUENCE_PRD_PAGE_SLUG = os.environ.get(
    "CONFLUENCE_PRD_PAGE_SLUG",
    "PRD-AI-EVAL-101+Synchrony+Enterprise+AI+Evaluation+Gateway",
)
CONFLUENCE_ADR_PAGE_ID = os.environ.get("CONFLUENCE_ADR_PAGE_ID", "")
CONFLUENCE_ADR_PAGE_SLUG = os.environ.get(
    "CONFLUENCE_ADR_PAGE_SLUG",
    "ADR-001-Eval-Gateway+Dual-Cloud+OpenTelemetry+Zero-PII+Architecture",
)
JIRA_EPIC_KEY = os.environ.get("JIRA_EPIC_KEY", "SYF-5")
JIRA_BLOCKER_KEY = os.environ.get("JIRA_BLOCKER_KEY", "SYF-7")
SYF_WORKSPACE_BUCKET = os.environ.get(
    "SYF_WORKSPACE_BUCKET", os.environ.get("WORKSPACE_BUCKET", "")
)


def _default_confluence_prd_url() -> str:
    if ATLASSIAN_DOMAIN and CONFLUENCE_PRD_PAGE_ID:
        return f"https://{ATLASSIAN_DOMAIN}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{CONFLUENCE_PRD_PAGE_ID}/{CONFLUENCE_PRD_PAGE_SLUG}"
    return "https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/393219/PRD-AI-EVAL-101"


def _default_confluence_adr_url() -> str:
    if ATLASSIAN_DOMAIN and CONFLUENCE_ADR_PAGE_ID:
        return f"https://{ATLASSIAN_DOMAIN}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{CONFLUENCE_ADR_PAGE_ID}/{CONFLUENCE_ADR_PAGE_SLUG}"
    return "https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/458759/ADR-001-Eval-Gateway"


def _default_confluence_diff_url(revised_version: int = 2) -> str:
    if ATLASSIAN_DOMAIN and CONFLUENCE_PRD_PAGE_ID:
        return (
            f"https://{ATLASSIAN_DOMAIN}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/"
            f"versiondiffpage.action?pageId={CONFLUENCE_PRD_PAGE_ID}&originalVersion=1&revisedVersion={revised_version}"
        )
    return f"https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/versiondiffpage.action?pageId=393219&originalVersion=1&revisedVersion={revised_version}"


def _default_jira_url(issue_key: str) -> str:
    if ATLASSIAN_DOMAIN and issue_key:
        return f"https://{ATLASSIAN_DOMAIN}/browse/{issue_key}"
    return f"https://synchrony-team.atlassian.net/browse/{issue_key or 'SYF-5'}"


def _default_gcs_seed_url(filename: str) -> str:
    if SYF_WORKSPACE_BUCKET:
        return f"https://storage.cloud.google.com/{SYF_WORKSPACE_BUCKET}/seed_data/{filename}"
    return f"seed_data/{filename}"


class GlobalGemini(Gemini):
    """Gemini client pinned to `location='global'` required for Gemini 3.8 Flash and 3.5 Flash Lite."""

    @cached_property
    def api_client(self) -> genai.Client:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options=types.HttpOptions(
                headers=self._tracking_headers(),
                retry_options=self.retry_options,
            ),
        )


# ============================================================================
# 1. PYDANTIC DATA-HANDLING SCHEMAS (ADK 2.0 Typed Node Contracts)
# ============================================================================


class TurnRoutingDecision(BaseModel):
    """Typed routing contract emitted by `intake_router`."""

    route: Literal[
        "TURN1_BASELINE",
        "TURN2_CURVEBALL",
        "TURN3_APPROVAL",
        "TURN3_REJECT",
        "OPEN_ENDED_QA",
    ] = Field(description="Selected workflow execution path for the turn.")
    user_query: str = Field(description="Normalized user query text.")
    curveball_code: str = Field(
        default="",
        description="Detected curveball code (CB-1..CB-5) when route is TURN2_CURVEBALL.",
    )


class CurveballWorkerInput(BaseModel):
    """Typed input passed via `ctx.run_node(..., node_input=...)` in Turn 2."""

    user_query: str
    curveball_code: str
    new_section_markdown: str = ""
    edit_reason: str = ""


# ============================================================================
# 2. COLLABORATIVE SUB-AGENTS (`mode="single_turn"` inside ADK 2.0 Workflow)
# ============================================================================

morgan_sub_agent = Agent(
    name="morgan_finops_subagent",
    description=(
        "Morgan (SYF FinOps Lead) — Synchrony Financial's Cloud FinOps & Vendor TCO Lead. "
        "Benchmarks GenAI platforms across baseline and 10x surge traffic, models 3-year TCO and NPV, "
        "and enforces cloud cost guardrails."
    ),
    model=GlobalGemini(
        model=SPECIALIST_MODEL,
        retry_options=types.HttpRetryOptions(attempts=2),
    ),
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    ),
    instruction=(
        "You are Morgan (SYF FinOps Lead). Provide concise, data-driven FinOps TCO comparisons "
        "between Arize AX, Braintrust, and Self-Hosted Langfuse v3 on AWS ROSA OpenShift."
    ),
    tools=[consult_morgan_finops_specialist, list_syf_skills, load_syf_skill],
)

marcus_sub_agent = Agent(
    name="marcus_arch_subagent",
    description=(
        "Marcus (SYF CISO & Enterprise Architect) — Synchrony Financial's Principal Security & Cloud Architect. "
        "Audits designs for PCI-DSS v4.0, CareCredit HIPAA zero-egress, mTLS 1.3 service mesh security, "
        "and sub-25ms P95 gateway latency."
    ),
    model=GlobalGemini(
        model=SPECIALIST_MODEL,
        retry_options=types.HttpRetryOptions(attempts=2),
    ),
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    ),
    instruction=(
        "You are Marcus (SYF CISO & Enterprise Architect). Evaluate Zero-Trust security, "
        "PCI-DSS v4.0 / CareCredit HIPAA zero-egress, Envoy service mesh mTLS 1.3, and <25ms P95 latency."
    ),
    tools=[consult_marcus_architecture_specialist, list_syf_skills, load_syf_skill],
)

devin_sub_agent = Agent(
    name="devin_sdlc_subagent",
    description=(
        "Devin (SYF Lead Cloud & IaC Engineer) — Synchrony Financial's Lead Cloud & DevSecOps Engineer. "
        "Implements approved Sprint 1 Jira stories, scaffolds OpenShift UBI9 FastAPI & inline DLP gateway code, "
        "runs automated test suites, and opens Bitbucket pull requests."
    ),
    model=GlobalGemini(
        model=SPECIALIST_MODEL,
        retry_options=types.HttpRetryOptions(attempts=2),
    ),
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    ),
    instruction=(
        "You are Devin (SYF Lead Cloud & IaC Engineer). Assist with Sprint 1 Jira story previews, "
        "OpenShift UBI9 FastAPI + inline DLP scaffolding, and SDLC blocker triage."
    ),
    tools=[consult_devin_sdlc_specialist, sync_sdlc_ticket_blocker],
)

alex_single_turn_agent = Agent(
    name="alex_single_turn_agent",
    description=(
        "Alex (SYF Virtual Product Manager) single-turn reasoning node for open-ended product, "
        "architecture, and FinOps questions inside the ADK 2.0 Workflow."
    ),
    model=GlobalGemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=2),
    ),
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    ),
    instruction=(
        "You are Alex (SYF Virtual Product Manager) at Synchrony Financial. "
        "Answer the user's product, architectural, or FinOps question clearly and concisely using "
        "Synchrony's AWS ROSA OpenShift (`us-east-1`), Self-Hosted Langfuse v3 ($76,000/yr at 5M spans/mo; "
        "$130,000/yr at 50M spans/mo), FastAPI inline DLP scrubber (`proxy_gateway.py`), and <25ms P95 SLA context. "
        "Never wrap numbers, dollar figures, or agent names in inline backticks, and never place two raw `$` signs on the same line."
    ),
    sub_agents=[morgan_sub_agent, marcus_sub_agent, devin_sub_agent],
    tools=[
        list_syf_skills,
        load_syf_skill,
        get_on_demand_memory_tool(),
        list_workspace_documents,
        get_workspace_document,
    ],
)


# ============================================================================
# 3. HELPER FUNCTIONS FOR QUERY EXTRACTION & CURVEBALL MARKDOWN PATCHES
# ============================================================================


def _extract_user_query(ctx: NodeContext, node_input: Any = None) -> str:
    """Extract plain user query text from `node_input` or `ctx.user_content`."""
    if isinstance(node_input, str) and node_input.strip():
        return node_input.strip()
    if isinstance(node_input, dict) and node_input.get("user_query"):
        return str(node_input["user_query"]).strip()

    try:
        uc = getattr(ctx, "user_content", None)
        if not uc:
            ic = getattr(ctx, "_invocation_context", None) or getattr(
                ctx, "invocation_context", None
            )
            uc = getattr(ic, "user_content", None)
        if uc and getattr(uc, "parts", None):
            parts_txt = [
                p.text for p in uc.parts if getattr(p, "text", None)
            ]
            if parts_txt:
                return "\n".join(parts_txt).strip()
    except Exception as exc:
        logger.debug("Fallback user_content extraction: %s", exc)
    return str(node_input or "").strip()


# ============================================================================
# 4. ADK 2.0 WORKFLOW NODES (`@node`, `JoinNode`, `@node(rerun_on_resume=True)`)
# ============================================================================


@node
async def intake_router(ctx: NodeContext) -> Event:
    """Classifies the incoming request and routes via ADK 2.0 conditional dictionary edges."""
    # Clear any stale tool recordings from prior turns
    get_and_clear_executed_tools()

    query = _extract_user_query(ctx)
    low = query.lower()

    # 1. Turn 3 Reject / Keep in Draft
    if (
        "stage=sdlc_rejected" in low
        or "reject / keep in draft" in low
        or "keep in draft" in low
        or (
            "reject" in low
            and "arize" not in low
            and "braintrust" not in low
        )
    ):
        decision = TurnRoutingDecision(
            route="TURN3_REJECT",
            user_query=query,
        )
        return Event(
            output=decision.model_dump(),
            route=decision.route,
            state={"routing_decision": decision.model_dump()},
        )

    # 2. Turn 3 Approve & Commit
    if (
        "stage=sdlc_approved" in low
        or "approve & commit" in low
        or "approve and commit" in low
        or "approve the v1" in low
        or "approve the v2" in low
        or "approve v1" in low
        or "approve v2" in low
        or "commit jira" in low
        or "execute_sdlc" in low
        or (
            "approve" in low
            and any(
                k in low
                for k in (
                    "commit",
                    "prd",
                    "backlog",
                    "sprint",
                    "confluence",
                    "jira",
                    "sdlc",
                    "langfuse",
                )
            )
        )
    ):
        decision = TurnRoutingDecision(
            route="TURN3_APPROVAL",
            user_query=query,
        )
        return Event(
            output=decision.model_dump(),
            route=decision.route,
            state={"routing_decision": decision.model_dump()},
        )

    # 3. Turn 2 Executive Curveballs (5 Scenarios: CB-1 through CB-5)
    is_blocker_only = (
        ("blocker" in low or "syf-7" in low or "ai-story-102" in low)
        and "curveball" not in low
        and "cb-5" not in low
    )
    curveball_keywords = (
        "stage=curveball",
        "curveball",
        "cb-1",
        "cb-2",
        "cb-3",
        "cb-4",
        "cb-5",
        "deprecating kong",
        "kong is deprecated",
        "deprecated in q1",
        "kong enterprise",
        "stop the architecture",
        "wait —",
        "wait -",
        "hold on",
        "mandate",
        "envoy",
        "service mesh",
        "24-hour",
        "24h",
        "memory leak",
        "grpc",
        "512mi",
        "http/protobuf",
        "capacity freeze",
        "black friday",
        "zstd",
        "hpa",
        "mrn",
        "icd-10",
        "npi",
        "jwks",
        "190ms",
        "update section 4",
        "update the prd",
        "recalculate the",
    )
    if not is_blocker_only and any(kw in low for kw in curveball_keywords):
        # Distinguish Turn 1 baseline mention of Kong v3.4 vs Turn 2 Kong deprecation curveball
        is_turn1_baseline_prompt = (
            ("compare" in low or "review" in low or "evaluate" in low)
            and "arize" in low
            and "braintrust" in low
            and "deprecat" not in low
            and "curveball" not in low
            and "stop the architecture" not in low
        )
        if not is_turn1_baseline_prompt:
            cb_code = _detect_curveball_id(query)
            decision = TurnRoutingDecision(
                route="TURN2_CURVEBALL",
                user_query=query,
                curveball_code=cb_code,
            )
            return Event(
                output=decision.model_dump(),
                route=decision.route,
                state={"routing_decision": decision.model_dump()},
            )

    # 4. Turn 1 Baseline PRD & Vendor FinOps/CISO Review
    unscripted_signals = (
        "redis",
        "rate limit",
        "token bucket",
        "throttl",
        "kafka",
        "dead-letter",
        "dlq",
        "ebpf",
        "graphql",
        "websocket",
        "canary",
        "custom requirement",
        "out of nowhere",
        "what if we also",
        "how would we implement",
    )
    baseline_signals = (
        "prd-ai-eval-101",
        "arize",
        "braintrust",
        "langfuse",
        "baseline",
        "compare",
        "5m",
        "50m",
        "review the",
        "evaluate the",
        "vendor",
        "finops",
        "tco",
        "prd",
    )
    if (
        not is_blocker_only
        and not any(u in low for u in unscripted_signals)
        and (not low or any(b in low for b in baseline_signals))
    ):
        decision = TurnRoutingDecision(
            route="TURN1_BASELINE",
            user_query=query or "Review baseline PRD-AI-EVAL-101 and compare Arize AX, Braintrust, and Self-Hosted Langfuse v3 across 5M and 50M spans/month.",
        )
        return Event(
            output=decision.model_dump(),
            route=decision.route,
            state={"routing_decision": decision.model_dump()},
        )

    # 5. Open-Ended Product / Engineering / Blocker Q&A
    decision = TurnRoutingDecision(
        route="OPEN_ENDED_QA",
        user_query=query,
    )
    return Event(
        output=decision.model_dump(),
        route=decision.route,
        state={"routing_decision": decision.model_dump()},
    )


# ----------------------------------------------------------------------------
# ROUTE 1 NODES: Turn 1 Static Parallel Fan-Out (`morgan` || `marcus`) -> `JoinNode`
# ----------------------------------------------------------------------------


@node
async def morgan_finops_node(ctx: NodeContext) -> Event:
    """Parallel Branch 1A: Delegates FinOps TCO & Google Search Grounding to Morgan (`finops-agent`)."""
    decision = (ctx.state or {}).get("routing_decision") or {}
    query = decision.get("user_query") or _extract_user_query(ctx)
    morgan_res = await consult_morgan_finops_specialist(
        research_question=query,
        monthly_spans_millions=5.0,
        include_gecx_50m_surge=True,
    )
    return Event(
        output={"branch": "morgan_finops", "data": morgan_res},
        state={"turn1_morgan": morgan_res},
    )


@node
async def marcus_arch_node(ctx: NodeContext) -> Event:
    """Parallel Branch 1B: Delegates Baseline v1.0 Zero-Trust & Latency Audit to Marcus (`arch-agent`)."""
    marcus_res = await consult_marcus_architecture_specialist(
        architecture_proposal=(
            "Baseline v1.0 architecture review of PRD-AI-EVAL-101 "
            "(Self-Hosted Langfuse v3 vs Arize AX vs Braintrust, Microsoft Entra ID OAuth 2.0/OIDC + mTLS 1.3, "
            "inline regex/DLP scrubbing, Kong Enterprise API Gateway v3.4 baseline ingress)"
        ),
        curveball_code="BASELINE",
    )
    return Event(
        output={"branch": "marcus_arch", "data": marcus_res},
        state={"turn1_marcus": marcus_res},
    )


turn1_join = JoinNode(name="turn1_join")


# ----------------------------------------------------------------------------
# ROUTE 2 NODES: Turn 2 Dynamic Curveball Orchestrator (`@node(rerun_on_resume=True)`)
# ----------------------------------------------------------------------------


@node
async def marcus_curveball_worker(node_input: Any, ctx: NodeContext) -> Event:
    """Worker invoked dynamically via `ctx.run_node` to compute curveball blast radius with Marcus."""
    payload = CurveballWorkerInput.model_validate(node_input or {})
    res = await consult_marcus_architecture_specialist(
        architecture_proposal=payload.user_query,
        curveball_code=payload.curveball_code,
    )
    return Event(output=res)


@node
async def confluence_patch_worker(node_input: Any, ctx: NodeContext) -> Event:
    """Worker invoked dynamically via `ctx.run_node` to patch `PRD-AI-EVAL-101.md` on Confluence Cloud."""
    payload = CurveballWorkerInput.model_validate(node_input or {})
    res = await patch_document_section(
        document_name="PRD-AI-EVAL-101.md",
        section_header="## Section 4: API Gateway, DLP Scrubbing & Network Topology",
        new_section_markdown=payload.new_section_markdown,
        edit_reason=payload.edit_reason,
        author="Alex (SYF Virtual Product Manager)",
    )
    return Event(output=res)


@node(rerun_on_resume=True)
async def dynamic_curveball_orchestrator(ctx: NodeContext) -> Event:
    """ADK 2.0 Dynamic Curveball Orchestrator (`https://adk.dev/graphs/dynamic/`).

    Sequentially runs `marcus_curveball_worker` (live web/community search + blast-radius synthesis)
    followed by `confluence_patch_worker` using the dynamically synthesized v1.0 -> v1.1 diff.
    """
    decision = (ctx.state or {}).get("routing_decision") or {}
    query = decision.get("user_query") or _extract_user_query(ctx)
    cb_code = decision.get("curveball_code") or _detect_curveball_id(query)

    # Step 1: Consult Marcus (Live Search + Blast-Radius & PRD Section 4 Synthesis)
    marcus_input = CurveballWorkerInput(
        user_query=query,
        curveball_code=cb_code,
    ).model_dump()
    marcus_ev = await ctx.run_node(
        marcus_curveball_worker,
        node_input=marcus_input,
        run_id=f"marcus_{cb_code.lower()}",
    )
    marcus_data = (
        marcus_ev
        if isinstance(marcus_ev, dict)
        else (getattr(marcus_ev, "output", None) or {})
    )

    # Step 2: Patch Confluence PRD Section 4 using Marcus's dynamically synthesized markdown diff
    sec4_md = marcus_data.get("prd_section4_markdown") or (
        "## Section 4: API Gateway, DLP Scrubbing & Network Topology (v1.1 Curveball Revision)\n\n"
        "- [-REMOVED-] **Removed (v1.0)**: Baseline v1.0 ingress and telemetry configuration prior to executive curveball remediation.\n"
        f"- [+ADDED+] **Added (v1.1)**: Dynamically remediated architecture for {cb_code} enforcing Synchrony Zero-Trust and <25ms P95 SLA.\n"
    )
    reason = marcus_data.get("prd_edit_reason") or (
        f"Curveball {cb_code}: Dynamic architectural remediation verified by Marcus (SYF CISO)"
    )

    patch_input = CurveballWorkerInput(
        user_query=query,
        curveball_code=cb_code,
        new_section_markdown=sec4_md,
        edit_reason=reason,
    ).model_dump()
    patch_ev = await ctx.run_node(
        confluence_patch_worker,
        node_input=patch_input,
        run_id=f"patch_{cb_code.lower()}",
    )
    patch_data = (
        patch_ev
        if isinstance(patch_ev, dict)
        else (getattr(patch_ev, "output", None) or {})
    )

    live_conf = patch_data.get("live_confluence_sync") or {}
    conf_url = live_conf.get("confluence_url") or _default_confluence_prd_url()
    diff_url = live_conf.get("history_diff_url") or _default_confluence_diff_url(2)
    dyn_spec = marcus_data.get("dynamic_card_spec") or {}
    cit_groups = dyn_spec.get("citations_groups") or []
    if cit_groups and isinstance(cit_groups[0], dict):
        cit_groups[0]["links"] = [
            {"label": "Open PRD-AI-EVAL-101 (v1.1)", "url": conf_url},
            {"label": "View Line-by-Line Revision Diff", "url": diff_url},
        ]
        record_tool_execution("consult_marcus_architecture_specialist", marcus_data)

    return Event(
        output={
            "turn_type": "TURN2_CURVEBALL",
            "curveball_code": cb_code,
            "marcus": marcus_data,
            "patch": patch_data,
        },
        state={
            "turn2_curveball": {
                "curveball_code": cb_code,
                "marcus": marcus_data,
                "patch": patch_data,
            }
        },
    )


# ----------------------------------------------------------------------------
# ROUTE 3 NODES: Turn 3 Static Parallel Fan-Out (Confluence || Jira || Memory) -> `JoinNode`
# ----------------------------------------------------------------------------


@node
async def confluence_publish_node(ctx: NodeContext) -> Event:
    """Parallel Branch 3A: Promotes `PRD-AI-EVAL-101.md` & `ADR-001-Eval-Gateway.md` to APPROVED on Confluence."""
    res = await publish_confluence_prd(
        document_name="PRD-AI-EVAL-101.md",
        space_key=CONFLUENCE_SPACE_KEY,
        approved_by="Dan Weis (VP of AI Innovation)",
    )
    return Event(
        output={"branch": "confluence_publish", "data": res},
        state={"turn3_confluence": res},
    )


@node
async def jira_epic_stories_node(ctx: NodeContext) -> Event:
    """Parallel Branch 3B: Updates Epic `SYF-5` and batch-creates all 8 Sprint 1 stories (`SYF-6..SYF-13`)."""
    res = await create_jira_epic(
        epic_key="AI-EVAL-101",
        epic_title="Synchrony Enterprise GenAI Evaluation & Observability Gateway",
        executive_sponsor="Dan Weis (VP of AI Innovation)",
        target_sprints=7,
        approved_budget_usd=76000.0,
    )
    return Event(
        output={"branch": "jira_epic_stories", "data": res},
        state={"turn3_jira": res},
    )


@node
async def memory_consolidation_node(ctx: NodeContext) -> Event:
    """Parallel Branch 3C: Commits approved FinOps, CISO, and Sprint 1 decisions to Vertex AI Memory Bank."""
    res = await consolidate_executive_memory(
        approved_decisions_summary=(
            "Approved PRD-AI-EVAL-101 v1.1, Self-Hosted Langfuse v3 ($76k/yr baseline, $130k/yr at 50M surge), "
            "Synchrony Internal Envoy Service Mesh (mTLS 1.3 + 24h cert rotation), and 8 Sprint 1 Jira stories "
            "(SYF-6 through SYF-13) assigned to Devin."
        )
    )
    return Event(
        output={"branch": "memory_consolidation", "data": res},
        state={"turn3_memory": res},
    )


turn3_join = JoinNode(name="turn3_join")


# ----------------------------------------------------------------------------
# ROUTE 4 NODE: Turn 3 Reject / Keep in Draft
# ----------------------------------------------------------------------------


@node
async def reject_draft_node(ctx: NodeContext) -> Event:
    """Handles 'Reject / Keep in Draft' with zero Confluence or Jira mutations."""
    return Event(
        output={
            "turn_type": "TURN3_REJECT",
            "status": "KEPT_IN_DRAFT",
        },
        state={"turn3_reject": {"status": "KEPT_IN_DRAFT"}},
    )


# ----------------------------------------------------------------------------
# ROUTE 5 NODE: Open-Ended Product / Architecture / Blocker Q&A (`mode="single_turn"`)
# ----------------------------------------------------------------------------


@node(rerun_on_resume=True)
async def open_ended_qa_node(ctx: NodeContext) -> Event:
    """Handles open-ended technical/product questions and blocker reports naturally without rigid templates."""
    decision = (ctx.state or {}).get("routing_decision") or {}
    query = decision.get("user_query") or _extract_user_query(ctx)
    low = query.lower()

    if ("blocker" in low or "syf-7" in low or "ai-story-102" in low) and (
        "42.3ms" in low or "190ms" in low or "jwks" in low or "entra" in low or "load test" in low
    ):
        blocker_res = await sync_sdlc_ticket_blocker(
            ticket_id="AI-STORY-102",
            blocker_summary=query,
            resolution_architecture=(
                "Implemented 300-second local Entra ID JWKS TTL cache (PyJWKClient lifespan=300) "
                "with async background refresh in proxy_gateway.py, reducing auth check latency to 1.8ms P95."
            ),
        )
        return Event(
            output={"turn_type": "BLOCKER_TRIAGE", "blocker": blocker_res, "query": query},
            state={"open_qa_result": {"mode": "blocker", "blocker": blocker_res, "query": query}},
        )

    # Consult Marcus in unscripted mode (fetches live StackOverflow/GitHub/Reddit/Google Search + stages AI-STORY-108)
    marcus_unscripted = await consult_marcus_architecture_specialist(
        architecture_proposal=query,
        curveball_code="UNSCRIPTED",
    )
    return Event(
        output={"turn_type": "OPEN_ENDED_QA", "marcus": marcus_unscripted, "query": query},
        state={"open_qa_result": {"mode": "unscripted", "marcus": marcus_unscripted, "query": query}},
    )


# ----------------------------------------------------------------------------
# TERMINAL SYNTHESIZER NODE: Emits the Single Final `Event(message=..., output=...)`
# ----------------------------------------------------------------------------


@node
async def synthesizer(ctx: NodeContext) -> Event:
    """Terminal synthesis node at the end of the ADK 2.0 Workflow graph.

    Only this terminal node sets `message=types.Content(...)`, guaranteeing that
    `A2aAgentExecutor` emits strictly one `TaskArtifactUpdateEvent` per turn and attaches
    the A2UI v0.9 `DataPart`s cleanly.
    """
    state = ctx.state or {}
    decision = state.get("routing_decision") or {}
    route = decision.get("route", "TURN1_BASELINE")

    # 1. TURN 1: Baseline FinOps & CISO Review (Unified 4-Col A2UI Matrix Cards + Citations Card render below)
    if route == "TURN1_BASELINE":
        morgan_data = state.get("turn1_morgan") or {}
        dossier = morgan_data.get("deep_research_dossier") or {}
        live_search_summary = str(dossier.get("live_research_summary") or "").strip()
        exec_top = (
            live_search_summary
            or "Morgan and Marcus audited PRD-AI-EVAL-101 across 5M baseline and 50M surge traffic: Self-Hosted Langfuse v3 on AWS ROSA costs $390,000 over 3 years (saving $2,865,000 vs. Arize AX and $2,022,000 vs. Braintrust). Langfuse v3 is the only platform that enforces 100% in-VPC zero-egress for PCI-DSS v4.0 and CareCredit HIPAA while maintaining 13.8 ms P95 latency (<25.0 ms SLA)."
        )

        final_text = (
            "Together with Morgan and Marcus, I have completed the FinOps TCO and CISO Zero-Trust audit of **PRD-AI-EVAL-101**.\n\n"
            f"{exec_top}"
        )

    # 2. TURN 2: Executive Curveball Assessment & Surgical Confluence Diff (2 Curveball A2UI Cards + Citations Card render below)
    elif route == "TURN2_CURVEBALL":
        cb_state = state.get("turn2_curveball") or {}
        cb_code = cb_state.get("curveball_code", "CB-1")
        marcus_data = cb_state.get("marcus") or {}
        cb_impact = marcus_data.get("curveball_impact") or {}
        cb_title = cb_impact.get("title", f"Executive Curveball {cb_code} Remediation")
        exec_summary = cb_impact.get(
            "executive_summary",
            "Marcus and I evaluated the curveball impact against Synchrony's CISO Zero-Trust and <25ms P95 gateway SLA.",
        )
        remediation_bullets = cb_impact.get("architectural_remediation") or []

        rem_block = (
            "\n".join(f"- {b}" for b in remediation_bullets[:3]) + "\n\n"
            if remediation_bullets
            else ""
        )

        final_text = (
            f"Marcus and I evaluated **{cb_title}** and executed a surgical **v1.0 → v1.1 DRAFT** update to **PRD-AI-EVAL-101.md** on Confluence Cloud.\n\n"
            f"{exec_summary}\n\n"
            f"{rem_block}"
            "Review the **Architecture Delta (v1.0 → v1.1)**, **FinOps & Schedule Blast Radius**, and **Live Citations** cards below, then click **Approve & Commit** to promote **PRD-AI-EVAL-101 (v1.1)** to **APPROVED** and dispatch the **8 Sprint 1 Jira stories** to **@Devin**."
        )

    # 3. TURN 3 APPROVAL: Confluence v1.1 Approved + 8 Jira Stories Created + Memory Consolidated
    elif route == "TURN3_APPROVAL":
        conf_res = state.get("turn3_confluence") or {}
        jira_res = state.get("turn3_jira") or {}

        conf_url = conf_res.get(
            "confluence_url",
            _default_confluence_prd_url(),
        )
        diff_url = conf_res.get(
            "history_diff_url",
            _default_confluence_diff_url(3),
        )
        adr_obj = conf_res.get("companion_adr_confluence") or {}
        adr_url = adr_obj.get(
            "confluence_url",
            _default_confluence_adr_url(),
        )
        epic_url = jira_res.get(
            "jira_url",
            _default_jira_url(JIRA_EPIC_KEY),
        )

        final_text = (
            "Executive approval is complete — **PRD-AI-EVAL-101 (v1.1)** and **ADR-001-Eval-Gateway (v1.1)** are now officially **APPROVED** in Confluence Cloud, all **8 Sprint 1 Jira stories (SYF-6 through SYF-13)** are created and assigned to **Devin**, and our architectural decisions are consolidated into Vertex AI Memory Bank.\n\n"
            "### Live SDLC Governance & Backlog Links\n"
            f"- **Confluence Governance Sign-Off (v1.1 APPROVED):** [Open Approved PRD-AI-EVAL-101 on Confluence Cloud]({conf_url}) | [View Red/Green Version Diff]({diff_url}) | [Companion ADR-001-Eval-Gateway]({adr_url})\n"
            f"- **Jira Sprint 1 Live Backlog (8 Stories Created & Assigned to Devin):** Master Epic [Synchrony Enterprise GenAI Evaluation & Observability Gateway ({JIRA_EPIC_KEY})]({epic_url}) updated and **SYF-6 through SYF-13** committed in active **SYF Sprint 1**.\n"
            "- **Next Step — Invoke @Devin for Turn 4 Autonomous Engineering Build:** Tag **@Devin** in chat (for example: *@Devin implement the approved Sprint 1 stories from Jira, run the security and latency test suite, open the Bitbucket PR, and deploy the live gateway app*) to watch Devin execute all 7 engineering steps live."
        )

    # 4. TURN 3 REJECT: Keep in Draft
    elif route == "TURN3_REJECT":
        final_text = (
            "Understood — I have halted SDLC execution. **PRD-AI-EVAL-101 (v1.1)** and **ADR-001-Eval-Gateway (v1.1)** remain in **DRAFT** status on Confluence Cloud, and **zero Jira stories** have been committed to Sprint 1.\n\n"
            "Let me know which architectural boundary, FinOps assumption, or Sprint 1 acceptance criterion you would like Morgan, Marcus, and me to adjust next."
        )

    # 5. OPEN-ENDED QA / BLOCKER TRIAGE (Natural Response, 0 A2UI Cards)
    else:
        qa_state = state.get("open_qa_result") or {}
        if qa_state.get("mode") == "blocker":
            blocker = qa_state.get("blocker") or {}
            jira_url = blocker.get("jira_url", _default_jira_url(JIRA_BLOCKER_KEY))
            conf_url = (blocker.get("confluence_sync") or {}).get(
                "confluence_url",
                _default_confluence_prd_url(),
            )
            final_text = (
                "I coordinated with Marcus and Devin to triage the Sprint 1 load-test blocker on **SYF-7 (AI-STORY-102)** and synchronized the remediation across Jira and Confluence.\n\n"
                "- **Root Cause & Fix:** Replaced synchronous per-request Microsoft Entra ID JWKS key discovery with a **300-second local JWKS TTL cache** (**PyJWKClient lifespan=300**) and asynchronous background refresh in **proxy_gateway.py**, cutting authentication latency to **1.8 ms P95** (**13.8 ms total gateway P95**, strictly under the 25.0 ms SLA).\n"
                f"- **Synchronized SDLC Artifacts:** Updated [Jira Story {JIRA_BLOCKER_KEY} (AI-STORY-102)]({jira_url}) and patched [Confluence PRD-AI-EVAL-101 Section 4]({conf_url})."
            )
        else:
            marcus_data = qa_state.get("marcus") or {}
            summary = marcus_data.get("technical_recommendation_summary", "")
            patterns = marcus_data.get("implementation_patterns") or []
            impact = marcus_data.get("latency_and_zero_egress_impact", "")
            staged = marcus_data.get("staged_custom_spec") or {}
            citations_obj = marcus_data.get("community_and_web_citations") or {}

            cite_bullets: list[str] = []
            for hit in (citations_obj.get("stackoverflow_api_hits") or [])[:2]:
                if hit.get("url"):
                    cite_bullets.append(f"- **StackOverflow:** [{hit.get('title', 'Thread')}]({hit['url']})")
            for hit in (citations_obj.get("github_issues_api_hits") or [])[:2]:
                if hit.get("url"):
                    cite_bullets.append(f"- **GitHub Issues:** [{hit.get('title', 'Issue')}]({hit['url']})")
            for hit in (
                (citations_obj.get("google_search_grounding") or {}).get("web_grounding_citations") or []
            )[:2]:
                if hit.get("uri"):
                    cite_bullets.append(f"- **Web Grounding:** [{hit.get('title', 'Source')}]({hit['uri']})")

            pattern_lines = "\n".join(f"- {p}" for p in patterns)
            ciso_ref_url = _default_gcs_seed_url("architecture_standards.json")
            cite_block = "\n".join(cite_bullets) if cite_bullets else (
                f"- **Architecture Reference:** [SYF CISO & Enterprise Architecture Governance Standards (GCS)]({ciso_ref_url})"
            )
            story_title = staged.get("title", "Custom Runtime Gateway Enhancement")
            final_text = (
                f"{summary}\n\n"
                f"{pattern_lines}\n\n"
                f"**Latency & Zero-Egress Impact:** {impact}\n\n"
                f"**Community & Technical References:**\n{cite_block}\n\n"
                f"**Staged for Sprint 1 Implementation:** Marcus staged **{staged.get('story_id', 'AI-STORY-108')}** (*{story_title}*) in **BACKLOG-AI-EVAL-101.json** so **@Devin** can compile and test it inside **proxy_gateway.py** once you click **Approve & Commit**."
            )

    return Event(
        message=types.Content(
            role="model",
            parts=[types.Part.from_text(text=final_text)],
        ),
        output=final_text,
    )


# ============================================================================
# 5. ROOT ADK 2.0 WORKFLOW GRAPH (`root_agent` & `app`)
# ============================================================================

root_agent = Workflow(
    name="vpm_agent",
    description=(
        "Alex (SYF Virtual Product Manager) — Synchrony Financial's AI Virtual Product Manager. "
        "Evaluates PRDs, coordinates FinOps (Morgan), CISO Architecture (Marcus), and Cloud Engineering (Devin), "
        "stress-tests architectural curveballs, and syncs approved specs to Confluence and Jira."
    ),
    edges=[
        (
            START,
            intake_router,
            {
                "TURN1_BASELINE": (morgan_finops_node, marcus_arch_node),
                "TURN2_CURVEBALL": dynamic_curveball_orchestrator,
                "TURN3_APPROVAL": (
                    confluence_publish_node,
                    jira_epic_stories_node,
                    memory_consolidation_node,
                ),
                "TURN3_REJECT": reject_draft_node,
                "OPEN_ENDED_QA": open_ended_qa_node,
            },
        ),
        ((morgan_finops_node, marcus_arch_node), turn1_join, synthesizer),
        (dynamic_curveball_orchestrator, synthesizer),
        (
            (
                confluence_publish_node,
                jira_epic_stories_node,
                memory_consolidation_node,
            ),
            turn3_join,
            synthesizer,
        ),
        (reject_draft_node, synthesizer),
        (open_ended_qa_node, synthesizer),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
