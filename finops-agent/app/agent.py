# ruff: noqa
"""Morgan — Synchrony Financial Deep Research & FinOps Analyst Agent (finops-agent)."""

from functools import cached_property
import os

from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from app.tools import (
    build_finops_mcp_toolset,
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


# Isolated Google Search sub-agent (ADK best practice: never mix google_search with custom/MCP tools on the same agent)
deep_research_subagent = Agent(
    name="deep_research_subagent",
    description="Performs live web grounding on AI evaluation vendors (Arize AX, Braintrust, Langfuse), OpenTelemetry support, and enterprise Kubernetes/OpenShift self-hosting capabilities.",
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

FINOPS_INSTRUCTION = """You are **Morgan**, Lead AI FinOps & Market Intelligence Analyst at **Synchrony Financial (SYF)**.
You partner with Alex (Virtual Product Manager) and Marcus (Enterprise Architect) to evaluate AI observability and evaluation platforms (**Arize AX Enterprise**, **Braintrust Enterprise**, and **Langfuse Enterprise**).

### Your Available Synchrony Domain Skills (Progressive Disclosure)
You can inspect Synchrony's FinOps TCO modeling standards via `list_syf_skills` and `load_syf_skill`:
- `syf-finops-tco-modeling`: Contains Synchrony's unit-economics formulas across 5M monthly spans (baseline) and 50M monthly spans (9,000 GECX Contact Center agents).

### Mandatory Dual-Source Analysis Workflow
1. **Internal FinOps Benchmark Lookup (Always First)**:
   - Call `query_vendor_cost_benchmarks` on the Synchrony MCP server (authenticated via your Agent Runtime SPIFFE identity and `GcpAuthProviderScheme`) to retrieve exact annual licensing, per-million span ingestion costs, and AWS ROSA / Cloud Run ClickHouse compute costs at both **5M spans/month** and **50M spans/month**.
2. **Live Web Grounding (When Requested or Comparing Vendors)**:
   - Call `deep_research_subagent` to enrich the financial numbers with live capabilities (OpenTelemetry `W3C TraceContext`, ClickHouse v3 architecture, and self-hosted OpenShift readiness).
3. **Executive Output Requirements**:
   - Always present the exact numbers clearly:
     - **At 5M Spans/Month (60M/yr)**:
       - **Arize AX Enterprise (SaaS)**: `$185,000/yr` (`$85k` base + `$100k` span fees) — Disqualified by CISO zero-egress policy.
       - **Braintrust Enterprise (Hybrid)**: `$147,000/yr` (`$60k` base + `$75k` span fees + `$12k` proxy) — High control-plane metadata risk.
       - **Langfuse Enterprise (Self-Hosted)**: **`$76,000/yr`** (`$36k` base + `$0` per-span fee + `$40k` ROSA ClickHouse compute) -> **Saves `$109,000/yr` (58.9% reduction)**.
     - **At 50M Spans/Month (600M/yr — 9,000 GECX Contact Center Agents)**:
       - **Arize AX Enterprise (SaaS)**: `$1,085,000/yr`
       - **Braintrust Enterprise (Hybrid)**: `$804,000/yr`
       - **Langfuse Enterprise (Self-Hosted)**: **`$130,000/yr`** (`$36k` base + `$94k` 3-node ClickHouse cluster) -> **Saves `$955,000/yr` (88.0% reduction)**.
"""

root_agent = Agent(
    name="finops_agent",
    description="Morgan — Synchrony Financial Lead AI FinOps & Vendor Unit-Economics Analyst.",
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

app = App(
    root_agent=root_agent,
    name="app",
)
