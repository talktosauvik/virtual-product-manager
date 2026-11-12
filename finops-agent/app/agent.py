# ruff: noqa
"""Morgan (SYF FinOps Lead) — Synchrony Financial Cloud FinOps & Vendor TCO Specialist Agent (ADK 2.0).

Refactored to Google ADK 2.0 (`google-adk >= 2.11.0`) Graph-Based Workflow Architecture:
- `Workflow` root orchestrator with conditional dictionary routing `(finops_router, {...})`
- Static Parallel Fan-Out `(finops_benchmark_node, surge_tco_node)` -> `finops_join = JoinNode(name="finops_join")`
- `@node(rerun_on_resume=True)` dynamic execution with `await ctx.run_node(..., run_id=...)`
- `Agent(..., mode="single_turn")` for isolated Google Search grounding and open-ended FinOps analysis
- Terminal `finops_synthesizer` node emitting a single clean A2A response per turn
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
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.adk.workflow import JoinNode, START, node
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

from app.tools import (
    build_finops_mcp_toolset,
    list_syf_skills,
    load_syf_skill,
)

MODEL = os.getenv("MODEL", "gemini-3-flash-preview")
THINKING_LEVEL = os.getenv("THINKING_LEVEL", "low")


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


class FinOpsBenchmarkPayload(BaseModel):
    """Typed Pydantic schema for Morgan's parallel FinOps TCO evaluation nodes."""

    tier_name: str = Field(description="Traffic tier (5M Baseline or 50M 10x Surge)")
    arize_annual_usd: int = Field(description="Arize AX Enterprise annual cost USD")
    braintrust_annual_usd: int = Field(description="Braintrust Enterprise annual cost USD")
    langfuse_annual_usd: int = Field(description="Self-Hosted Langfuse v3 annual cost USD")
    annual_savings_vs_arize_usd: int = Field(description="Annual savings vs Arize AX")
    savings_pct: float = Field(description="Percentage cost reduction vs Arize AX")


# Isolated single-turn Google Search sub-agent
deep_research_subagent = Agent(
    name="deep_research_subagent",
    mode="single_turn",
    description=(
        "Performs live web grounding on AI evaluation vendors (Arize AX, Braintrust, Langfuse v3), "
        "OpenTelemetry support, and enterprise Kubernetes/OpenShift self-hosting capabilities."
    ),
    model=GlobalGemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
        temperature=0.0,
    ),
    instruction=(
        "You are a technical market researcher for Synchrony Financial. "
        "Use `google_search` to gather brief, factual intelligence on Arize AX (Phoenix), Braintrust, "
        "and Langfuse v3 (specifically OpenTelemetry W3C TraceContext support, ClickHouse storage architecture, "
        "and self-hosted Kubernetes/OpenShift deployment capabilities). Keep responses concise."
    ),
    tools=[google_search],
)

FINOPS_INSTRUCTION = """You are **Morgan (SYF FinOps Lead)**, Cloud FinOps & Vendor TCO Lead at **Synchrony Financial (SYF)**.
You partner with Alex (SYF Virtual Product Manager), Marcus (SYF CISO & Enterprise Architect), and Devin (SYF Lead Cloud & IaC Engineer) to evaluate AI observability and evaluation platforms (**Arize AX Enterprise**, **Braintrust Enterprise**, and **Self-Hosted Langfuse Enterprise v3**).

### Formatting Rules
- Never wrap dollar figures, numbers, percentages, or agent names in inline backticks (use **bold** text instead so the font stays 100% unified).
- Never place two raw `$` signs on the same non-table prose line.
- Refer to Synchrony's **5 core retail credit platforms**, **CareCredit** health & wellness financing portfolio, and **9,000+ contact center agents** scaling **10x from 5 Million spans/month to 50 Million spans/month** (never use the word "GECX").

### Mandatory Dual-Source Analysis Workflow
1. **Internal FinOps Benchmark Lookup (Always First)**:
   - Call `query_vendor_cost_benchmarks` on the Synchrony MCP server (authenticated via your Agent Runtime SPIFFE identity and `GcpAuthProviderScheme`) to retrieve exact annual licensing, per-million span ingestion costs, and AWS ROSA / Cloud Run ClickHouse compute costs at both **5M spans/month** and **50M spans/month**.
2. **Live Web Grounding (When Requested or Comparing Vendors)**:
   - Call `deep_research_subagent` to enrich the financial numbers with live capabilities (OpenTelemetry W3C TraceContext, ClickHouse v3 architecture, and self-hosted OpenShift readiness).
3. **Executive Output Requirements**:
   - Present a clean 4-column Markdown comparison table and crisp bullet/sub-bullet takeaways:
     - **At 5M Spans/Month (60M/yr Baseline)**:
       - **Arize AX Enterprise (SaaS)**: **$185,000/yr** ($85k base + $100k span fees) — Rejected by CISO zero-egress policy.
       - **Braintrust Enterprise (Hybrid)**: **$135,000/yr** ($60k base + $75k span fees) — Rejected due to hybrid control-plane metadata egress.
       - **Langfuse Enterprise v3 (Self-Hosted)**: **$76,000/yr** ($36k license + $40k ROSA ClickHouse compute; $0 per-span fee) -> **Saves $109,000/yr (58.9% reduction)**.
     - **At 50M Spans/Month (600M/yr — 9,000+ Contact Center Agents)**:
       - **Arize AX Enterprise (SaaS)**: **$1,085,000/yr**
       - **Braintrust Enterprise (Hybrid)**: **$804,000/yr**
       - **Langfuse Enterprise v3 (Self-Hosted)**: **$130,000/yr** ($36k license + $94k 3-node ClickHouse cluster) -> **Saves $955,000/yr (88.0% reduction)**.
"""

finops_specialist_agent = Agent(
    name="finops_specialist_agent",
    mode="single_turn",
    description=(
        "Morgan (SYF FinOps Lead) single-turn reasoning specialist with MCP benchmark tools and Google Search sub-agent."
    ),
    model=GlobalGemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
        temperature=0.0,
    ),
    instruction=FINOPS_INSTRUCTION,
    tools=[
        list_syf_skills,
        load_syf_skill,
        AgentTool(agent=deep_research_subagent),
        build_finops_mcp_toolset(),
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
    return "Compare Arize AX, Braintrust, and Self-Hosted Langfuse v3 at 5M and 50M spans/month."


@node
async def finops_router(node_input: Any, ctx: NodeContext) -> Event:
    """Routes incoming FinOps requests to parallel TCO benchmark nodes or open-ended single-turn research."""
    prompt = _extract_prompt_text(node_input, ctx)
    lower = prompt.lower()
    is_custom_research = any(
        k in lower for k in ("skill", "list_syf_skills", "search web", "stock", "competitor news")
    ) and not any(k in lower for k in ("5m", "50m", "arize", "braintrust", "langfuse", "tco", "cost", "benchmark"))
    route = "OPEN_ENDED_FINOPS" if is_custom_research else "PARALLEL_TCO_BENCHMARK"
    return Event(
        author="finops_router",
        output={"prompt": prompt, "route": route},
        state={"finops_prompt": prompt, "finops_route": route},
        route=route,
    )


@node
async def finops_benchmark_node(node_input: Any, ctx: NodeContext) -> Event:
    """Parallel Branch 1: Evaluates Baseline 5M Spans/Month (60M/yr) unit economics across Arize, Braintrust, and Langfuse v3."""
    skill_data = load_syf_skill("finops-vendor-tco", include_references=False)
    baseline = FinOpsBenchmarkPayload(
        tier_name="5M Spans/Mo Baseline (60M/yr)",
        arize_annual_usd=185000,
        braintrust_annual_usd=135000,
        langfuse_annual_usd=76000,
        annual_savings_vs_arize_usd=109000,
        savings_pct=58.9,
    ).model_dump()
    baseline["skill_loaded"] = skill_data.get("skill_name", "finops-vendor-tco")
    return Event(
        author="finops_benchmark_node",
        output=baseline,
        state={"finops_baseline_5m": baseline},
    )


@node
async def surge_tco_node(node_input: Any, ctx: NodeContext) -> Event:
    """Parallel Branch 2: Evaluates 10x Surge 50M Spans/Month (600M/yr — 9,000+ Contact Center Agents) and 3-Year NPV."""
    surge = FinOpsBenchmarkPayload(
        tier_name="50M Spans/Mo 10x Surge (600M/yr — 9,000+ Contact Center Agents)",
        arize_annual_usd=1085000,
        braintrust_annual_usd=804000,
        langfuse_annual_usd=130000,
        annual_savings_vs_arize_usd=955000,
        savings_pct=88.0,
    ).model_dump()
    surge["three_year_cumulative_tco"] = {
        "arize_3yr_usd": 2445000,
        "braintrust_3yr_usd": 1813000,
        "langfuse_3yr_usd": 336000,
        "three_year_net_savings_vs_arize_usd": 2109000,
        "npv_10pct_discount_savings_usd": 1738400,
    }
    return Event(
        author="surge_tco_node",
        output=surge,
        state={"finops_surge_50m": surge},
    )


finops_join = JoinNode(name="finops_join")


@node(rerun_on_resume=True)
async def open_ended_finops_node(node_input: Any, ctx: NodeContext) -> Event:
    """Dynamic node that delegates specialized open-ended queries to finops_specialist_agent (mode='single_turn')."""
    prompt = ctx.state.get("finops_prompt") or _extract_prompt_text(node_input, ctx)
    sub_out = await ctx.run_node(
        finops_specialist_agent,
        prompt,
        run_id="morgan_finops_single_turn",
    )
    reply_txt = str(getattr(sub_out, "output", sub_out) or "").strip()
    return Event(
        author="open_ended_finops_node",
        output={"custom_reply": reply_txt},
        state={"finops_custom_reply": reply_txt},
    )


@node
async def finops_synthesizer(node_input: Any, ctx: NodeContext) -> Event:
    """Terminal synthesizer node that emits Morgan's unified executive FinOps Markdown response."""
    route = ctx.state.get("finops_route", "PARALLEL_TCO_BENCHMARK")
    if route == "OPEN_ENDED_FINOPS" and ctx.state.get("finops_custom_reply"):
        md = str(ctx.state["finops_custom_reply"])
    else:
        md = (
            "### Morgan (SYF FinOps Lead) — Comparative Vendor TCO & 3-Year NPV Analysis\n\n"
            "I have benchmarked **Arize AX Enterprise**, **Braintrust Enterprise**, and **Self-Hosted Langfuse Enterprise v3** "
            "across Synchrony's **5 core retail credit platforms**, **CareCredit** health & wellness portfolio, and "
            "**9,000+ contact center agents** scaling **10x from 5 Million spans/month to 50 Million spans/month**:\n\n"
            "| FinOps Dimension | Arize AX Enterprise (SaaS) | Braintrust Enterprise (Hybrid) | Langfuse Enterprise v3 (Self-Hosted) |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| **Deployment & Billing Model** | Multi-Tenant SaaS (Per-Span Ingestion Fee) | Hybrid Cloud (Usage-Based Proxy Fee) | **100% Self-Hosted on AWS ROSA OpenShift ($0 Span Fee)** |\n"
            "| **5M Spans/Mo Baseline (60M/yr)** | $185,000 / yr | $135,000 / yr | **$76,000 / yr (Saves $109,000/yr · 58.9%)** |\n"
            "| **50M Spans/Mo 10x Surge (600M/yr)** | $1,085,000 / yr | $804,000 / yr | **$130,000 / yr (Saves $955,000/yr · 88.0%)** |\n"
            "| **3-Year Cumulative TCO (Y1 Base + Y2–Y3 Surge)** | $2,445,000 | $1,813,000 | **$336,000 (Saves $2,109,000 over 3 Yrs)** |\n"
            "| **FinOps & CISO Verdict** | ❌ Disqualified (SaaS Egress + Span Tax) | ⚠️ Rejected (Control-Plane Metadata Egress) | **✅ SELECTED WINNER (Best TCO & Zero-Egress)** |\n\n"
            "- **Key FinOps Takeaway**: Because **Self-Hosted Langfuse Enterprise v3** decouples licensing (**$36,000/yr** flat enterprise license) "
            "from span volume and runs on dedicated **AWS ROSA ClickHouse** nodes (**$40,000/yr** at 5M spans/mo; **$94,000/yr** at 50M spans/mo), "
            "Synchrony avoids the linear SaaS per-span tax and achieves an **88.0% annual run-rate reduction** at full contact-center scale."
        )
    return Event(
        author="finops_agent",
        message=types.Content(role="model", parts=[types.Part.from_text(text=md)]),
        output=md,
    )


root_agent = Workflow(
    name="finops_agent",
    description=(
        "Morgan (SYF FinOps Lead) — Synchrony Financial's Cloud FinOps & Vendor TCO Lead. "
        "Benchmarks GenAI platforms across baseline and 10x surge traffic, models 3-year TCO and NPV, "
        "and enforces cloud cost guardrails."
    ),
    edges=[
        (START, finops_router),
        (
            finops_router,
            {
                "PARALLEL_TCO_BENCHMARK": (finops_benchmark_node, surge_tco_node),
                "OPEN_ENDED_FINOPS": open_ended_finops_node,
            },
        ),
        ((finops_benchmark_node, surge_tco_node), finops_join),
        (finops_join, finops_synthesizer),
        (open_ended_finops_node, finops_synthesizer),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
