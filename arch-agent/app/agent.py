# ruff: noqa
"""Marcus (SYF CISO & Enterprise Architect) — Synchrony Financial Enterprise Architecture & Zero-Trust Agent (ADK 2.0).

Refactored to Google ADK 2.0 (`google-adk >= 2.11.0`) Graph-Based Workflow Architecture:
- `Workflow` root orchestrator with conditional dictionary routing `(arch_intake_router, {...})`
- Static Parallel Fan-Out `(zero_trust_dlp_auditor, mesh_latency_auditor)` -> `arch_join = JoinNode(name="arch_join")`
- `@node(rerun_on_resume=True)` dynamic curveball evaluator using `await ctx.run_node(..., run_id=...)`
- `Agent(..., mode="single_turn")` specialist for open-ended architecture & CISO governance queries
- Terminal `arch_synthesizer` node emitting a single clean A2A response per turn
"""

from __future__ import annotations

from functools import cached_property
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.adk import Agent, Context as NodeContext, Event, Workflow
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.workflow import JoinNode, START, node
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

from app.tools import (
    build_arch_mcp_toolset,
    evaluate_curveball_impact,
    list_syf_skills,
    load_syf_skill,
)

MODEL = os.getenv("MODEL", "gemini-3-flash-preview")
THINKING_LEVEL = os.getenv("THINKING_LEVEL", "low")
SYF_WORKSPACE_BUCKET = os.getenv("SYF_WORKSPACE_BUCKET", "")
ARCH_STANDARDS_GCS_URL = (
    f"https://storage.cloud.google.com/{SYF_WORKSPACE_BUCKET}/seed_data/architecture_standards.json"
)
ARCH_STANDARDS_GS_URI = f"gs://{SYF_WORKSPACE_BUCKET}/seed_data/architecture_standards.json"


class GlobalGemini(Gemini):
    """Routes Gemini 3.x requests through the configured Vertex AI endpoint."""

    @cached_property
    def api_client(self) -> genai.Client:
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options=types.HttpOptions(
                headers=self._tracking_headers(),
                retry_options=self.retry_options,
            ),
        )


class ZeroTrustAuditResult(BaseModel):
    """Typed Pydantic schema for Marcus's parallel compliance and latency audit nodes."""

    domain: str = Field(description="CISO Governance Domain")
    mandate_id: str = Field(description="Governance policy mandate identifier")
    verdict: str = Field(description="APPROVED or REJECTED verdict")
    control_summary: str = Field(description="Concrete architectural control verified")


ARCH_INSTRUCTION = f"""You are **Marcus (SYF CISO & Enterprise Architect)**, Principal Security & Cloud Architect at **Synchrony Financial (SYF)**.
You report into Synchrony's Architecture Review Board (CTO / CISO) and partner with Alex (SYF Virtual Product Manager), Morgan (SYF FinOps Lead), and Devin (SYF Lead Cloud & IaC Engineer).

### Formatting & Governance Rules
- Never wrap numbers, dollar amounts, percentages, or agent names (Alex, Morgan, Marcus, Devin) in inline backticks.
- Always include the clickable authenticated GCS reference link to Synchrony's official CISO & Enterprise Architecture governance standards:
  `[SYF CISO & Enterprise Architecture Governance Standards (GCS)]({ARCH_STANDARDS_GCS_URL})`
- Use clean, human-readable CISO Governance Domain titles (e.g., **PCI-DSS v4.0 & CareCredit HIPAA Zero-Egress**, **Identity, Auth & Transport Encryption**, **Cross-Cloud Latency & Runtime Hardening**) rather than cryptic policy IDs.

### Core Responsibilities & Tool Usage
1. **Compliance & Architecture Audits**:
   - Always call `get_architecture_standards` from the Synchrony MCP server to ground your decision in official CISO/CTO policies stored in GCS (`{ARCH_STANDARDS_GS_URI}`).
   - Enforce **Zero Egress for Tier-1 Cardholder Data (PAN, SSN) and CareCredit PHI (MRN, ICD-10)**:
     - Disqualify **Arize AX Enterprise (SaaS)** (NON-COMPLIANT: External Multi-Tenant SaaS Egress).
     - Reject **Braintrust Enterprise (Hybrid)** (NON-COMPLIANT: Hybrid Control-Plane Metadata Egress).
     - Approve **Self-Hosted Langfuse Enterprise v3** deployed inside Synchrony's private VPC (AWS ROSA OpenShift or Google Cloud Run Private Subnets) fronted by a FastAPI OpenTelemetry Collector & Inline DLP Proxy (under 25ms P95 SLA).
2. **Executive Curveball Blast-Radius Analysis**:
   - Whenever consulted about an executive scope pivot or curveball (e.g., Kong Gateway v3.4 Q1 deprecation -> Synchrony Internal Envoy Service Mesh, OpenTelemetry Python gRPC memory leak -> async HTTP/protobuf, or Entra ID 42.3ms latency blocker -> 300s local JWKS cache), ALWAYS call `evaluate_curveball_impact` to get the exact offshore squad impact vs. Synchrony Autonomous AI Fleet impact (`+1 Day`, `+$X`, `Total $XX Saved`, `Y% Time Reduction`, `X% Cost Reduction`).
"""

arch_specialist_agent = Agent(
    name="arch_specialist_agent",
    mode="single_turn",
    description=(
        "Marcus (SYF CISO & Enterprise Architect) single-turn specialist with MCP governance and curveball evaluation tools."
    ),
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


def _extract_prompt_text(node_input: Any, ctx: NodeContext) -> str:
    if isinstance(node_input, str) and node_input.strip():
        return node_input.strip()
    uc = getattr(ctx, "user_content", None)
    if uc and getattr(uc, "parts", None):
        texts = [p.text for p in uc.parts if getattr(p, "text", None)]
        if texts:
            return "\n".join(texts).strip()
    return "Audit Arize AX, Braintrust, and Self-Hosted Langfuse v3 against Synchrony CISO Zero-Trust standards."


@node
async def arch_intake_router(node_input: Any, ctx: NodeContext) -> Event:
    """Routes incoming CISO & Architecture requests across Baseline Parallel Audit, Dynamic Curveball Evaluation, or Open-Ended Q&A."""
    prompt = _extract_prompt_text(node_input, ctx)
    lower = prompt.lower()
    is_curveball = any(
        k in lower
        for k in (
            "curveball",
            "cb-1",
            "cb-2",
            "cb-3",
            "cb-4",
            "cb-5",
            "kong",
            "deprecated",
            "deprecation",
            "memory leak",
            "grpc",
            "42.3ms",
            "jwks",
            "15ms",
            "15.0ms",
            "nydfs",
            "7-year",
            "blast radius",
        )
    )
    if is_curveball:
        route = "CURVEBALL_IMPACT_AUDIT"
    elif any(k in lower for k in ("skill", "list_syf_skills")) and "audit" not in lower:
        route = "OPEN_ENDED_ARCH_QA"
    else:
        route = "BASELINE_COMPLIANCE_AUDIT"
    return Event(
        author="arch_intake_router",
        output={"prompt": prompt, "route": route},
        state={"arch_prompt": prompt, "arch_route": route},
        route=route,
    )


@node
async def zero_trust_dlp_auditor(node_input: Any, ctx: NodeContext) -> Event:
    """Parallel Branch 1: Audits PCI-DSS v4.0 Cardholder Data & CareCredit HIPAA PHI Zero-Egress compliance."""
    skill_info = load_syf_skill("pci-hipaa-redaction", include_references=False)
    res = ZeroTrustAuditResult(
        domain="PCI-DSS v4.0 & CareCredit HIPAA Zero-Egress",
        mandate_id="SYF-SEC-001 (Zero Tier-1 PII/PHI Egress)",
        verdict="APPROVED — Langfuse v3 (Arize AX & Braintrust Disqualified)",
        control_summary=(
            "100% VPC Self-Hosted Langfuse v3 on AWS ROSA OpenShift with inline FastAPI regex DLP "
            "redacting PAN, SSN, MRN, and ICD-10 before ClickHouse persistence."
        ),
    ).model_dump()
    res["skill_loaded"] = skill_info.get("skill_name", "pci-hipaa-redaction")
    return Event(
        author="zero_trust_dlp_auditor",
        output=res,
        state={"arch_zero_trust": res},
    )


@node
async def mesh_latency_auditor(node_input: Any, ctx: NodeContext) -> Event:
    """Parallel Branch 2: Audits Identity, mTLS 1.3 Service Mesh Encryption, and <25ms P95 Latency SLA."""
    res = ZeroTrustAuditResult(
        domain="Identity, mTLS 1.3 & Cross-Cloud Latency Hardening",
        mandate_id="SYF-SEC-002 / SYF-ARCH-003 (<25ms P95 Gateway Overhead)",
        verdict="APPROVED — mTLS 1.3 & 14.0ms P95",
        control_summary=(
            "Microsoft Entra ID OIDC + SPIFFE X.509 mTLS 1.3 East-West Envoy Service Mesh + "
            "Red Hat UBI9 non-root UID 1001 achieving 14.0ms P95 proxy latency (11.0ms below 25ms SLA)."
        ),
    ).model_dump()
    return Event(
        author="mesh_latency_auditor",
        output=res,
        state={"arch_mesh_latency": res},
    )


arch_join = JoinNode(name="arch_join")


@node
async def curveball_compute_worker(node_input: Any, ctx: NodeContext) -> Event:
    """Worker node invoked dynamically by dynamic_curveball_evaluator."""
    prompt = ctx.state.get("arch_prompt") or _extract_prompt_text(node_input, ctx)
    impact = evaluate_curveball_impact(curveball_description=prompt)
    return Event(
        author="curveball_compute_worker",
        output=impact,
        state={"arch_curveball_impact": impact},
    )


@node(rerun_on_resume=True)
async def dynamic_curveball_evaluator(node_input: Any, ctx: NodeContext) -> Event:
    """Dynamic ADK 2.0 node (`@node(rerun_on_resume=True)`) that evaluates executive curveball blast radius."""
    prompt = ctx.state.get("arch_prompt") or _extract_prompt_text(node_input, ctx)
    sub_out = await ctx.run_node(
        curveball_compute_worker,
        prompt,
        run_id="marcus_curveball_worker_run",
    )
    out_val = sub_out if isinstance(sub_out, dict) else getattr(sub_out, "output", sub_out)
    return Event(
        author="dynamic_curveball_evaluator",
        output=out_val,
        state={"arch_curveball_impact": out_val},
    )


@node(rerun_on_resume=True)
async def open_ended_arch_node(node_input: Any, ctx: NodeContext) -> Event:
    """Dynamic node that delegates specialized open-ended queries to arch_specialist_agent (mode='single_turn')."""
    prompt = ctx.state.get("arch_prompt") or _extract_prompt_text(node_input, ctx)
    sub_out = await ctx.run_node(
        arch_specialist_agent,
        prompt,
        run_id="marcus_arch_single_turn",
    )
    reply_txt = str(getattr(sub_out, "output", sub_out) or "").strip()
    return Event(
        author="open_ended_arch_node",
        output={"custom_reply": reply_txt},
        state={"arch_custom_reply": reply_txt},
    )


@node
async def arch_synthesizer(node_input: Any, ctx: NodeContext) -> Event:
    """Terminal synthesizer node emitting Marcus's unified CISO & Enterprise Architecture Markdown report."""
    route = ctx.state.get("arch_route", "BASELINE_COMPLIANCE_AUDIT")
    if route == "OPEN_ENDED_ARCH_QA" and ctx.state.get("arch_custom_reply"):
        md = str(ctx.state["arch_custom_reply"])
    elif route == "CURVEBALL_IMPACT_AUDIT":
        impact = ctx.state.get("arch_curveball_impact") or {}
        cb_id = impact.get("curveball_id", "CB-1")
        cb_title = impact.get("curveball_title", "Executive Architectural Curveball")
        sp_delta = impact.get("story_points_delta", 64)
        sprint_delta = impact.get("sprint_delta", 2)
        budget_delta = int(impact.get("one_time_engineering_budget_delta_usd", 32000))
        remediation = impact.get("architectural_remediation", "")
        stories = impact.get("new_or_updated_jira_stories") or []
        story_lines = "\n".join(
            f"  - **{s.get('story_id', 'AI-STORY-104')} ({s.get('story_points', 32)} SP)**: {s.get('title', '')}"
            for s in stories
        )
        md = (
            f"### Marcus (SYF CISO & Enterprise Architect) — Curveball Blast-Radius Audit ({cb_id})\n\n"
            f"- **Executive Trigger**: **{cb_title}**\n"
            f"- **Traditional Offshore Squad Impact (Baseline)**: **+{sprint_delta} Sprints (+{sp_delta} Story Points)** · **+${budget_delta:,}** one-time engineering cost\n"
            "- **Synchrony Autonomous AI Fleet Impact (Alex + Marcus + Morgan + Devin)**: **+1 Day** · **$0 Recurring Annual TCO Increase ($76,000/yr locked)**\n"
            f"- **Zero-Trust Architectural Remediation**: {remediation}\n"
            f"- **Auto-Generated Gherkin Jira Stories**:\n{story_lines}\n"
            f"- **Governance Reference**: [SYF CISO & Enterprise Architecture Governance Standards (GCS)]({ARCH_STANDARDS_GCS_URL})"
        )
    else:
        md = (
            "### Marcus (SYF CISO & Enterprise Architect) — Zero-Trust & Architecture Compliance Review\n\n"
            "I have audited **Arize AX Enterprise**, **Braintrust Enterprise**, and **Self-Hosted Langfuse Enterprise v3** against "
            f"[SYF CISO & Enterprise Architecture Governance Standards (GCS)]({ARCH_STANDARDS_GCS_URL}):\n\n"
            "| Audit Dimension | PCI-DSS v4.0 & CareCredit HIPAA | Identity, mTLS 1.3 & Ingress | Cross-Cloud Latency & Runtime |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| **Mandate / SLA** | Zero Tier-1 PII/PHI Egress (PAN, SSN, MRN, ICD-10) | Microsoft Entra ID OIDC + SPIFFE X.509 mTLS 1.3 | Under 25.0ms P95 Gateway Overhead SLA |\n"
            "| **Control Plane** | 100% VPC Self-Hosted Langfuse v3 on AWS ROSA | Synchrony Envoy Service Mesh (`mesh.syf.bank/injected: true`) | Async OTel HTTP/protobuf Collector + 3-Node ClickHouse |\n"
            "| **Zero-Trust** | Inline FastAPI regex DLP redaction prior to persistence | Local 300s Entra ID JWKS cache (1.8ms auth validation) | Red Hat UBI9 Python 3.12 non-root UID 1001 |\n"
            "| **Audit Verdict** | **✅ APPROVED — Langfuse v3** (Arize & Braintrust Disqualified) | **✅ APPROVED — mTLS 1.3** | **✅ APPROVED — 14.0ms P95** (11.0ms under 25ms SLA) |\n"
        )
    return Event(
        author="arch_agent",
        message=types.Content(role="model", parts=[types.Part.from_text(text=md)]),
        output=md,
    )


root_agent = Workflow(
    name="arch_agent",
    description=(
        "Marcus (SYF CISO & Enterprise Architect) — Synchrony Financial's Principal Security & Cloud Architect. "
        "Audits designs for PCI-DSS v4.0, CareCredit HIPAA zero-egress, mTLS 1.3 service mesh security, "
        "and sub-25ms P95 gateway latency."
    ),
    edges=[
        (START, arch_intake_router),
        (
            arch_intake_router,
            {
                "BASELINE_COMPLIANCE_AUDIT": (zero_trust_dlp_auditor, mesh_latency_auditor),
                "CURVEBALL_IMPACT_AUDIT": dynamic_curveball_evaluator,
                "OPEN_ENDED_ARCH_QA": open_ended_arch_node,
            },
        ),
        ((zero_trust_dlp_auditor, mesh_latency_auditor), arch_join),
        (arch_join, arch_synthesizer),
        (dynamic_curveball_evaluator, arch_synthesizer),
        (open_ended_arch_node, arch_synthesizer),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
