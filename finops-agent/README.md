# `finops-agent` — Morgan (Deep Research & FinOps Lead)

**Morgan (`finops-agent`)** is the specialist Cloud FinOps and vendor benchmark agent (modeled for a large financial institution). Built on **Google ADK 2.0 (`Workflow` Parallel Fan-Out + `JoinNode`)** and deployed on **Vertex AI Agent Runtime (`ReasoningEngine`)**, Morgan combines GCS telemetry benchmarks (`eval_vendor_benchmarks.json`) with live Google Search grounding to evaluate AI evaluation platforms (**Arize AX Enterprise**, **Braintrust Enterprise**, **Self-Hosted Langfuse Enterprise v3**), cross-cloud egress tariffs, and deterministic 1-year and 3-year Total Cost of Ownership (TCO) models at both `5M` baseline and `50M` monthly surge trace volumes.

---

## 1. Architecture & Runtime Profile

- **Framework**: Google ADK 2.0 (`Workflow` graph with `(finops_benchmark_node, surge_tco_node)` parallel fan-out → `finops_join = JoinNode`)
- **Model**: `MODEL=gemini-3-flash-preview` (`THINKING_LEVEL=low`, `GOOGLE_CLOUD_LOCATION=global`)
- **Deployment Target**: Vertex AI Agent Runtime (`deployment_target: agent_runtime`, `is_a2a: true`)
- **Authentication**: Resolves MCP credentials dynamically via **GCP Agent Identity Auth Manager** (`GcpAuthProvider` + `AuthProviderCredentialsServiceClient`).

---

## 2. Core Tools (`app/tools.py` & `app/agent.py`)

- **`query_vendor_cost_benchmarks`** *(via `syf-mcp-server` `McpToolset`)*: Loads `seed_data/eval_vendor_benchmarks.json` from GCS (`gs://${SYF_WORKSPACE_BUCKET}`) and computes deterministic 1-year and 3-year TCO across Arize AX, Braintrust, and Self-Hosted Langfuse v3 (ClickHouse ZSTD on AWS ROSA OpenShift) at `5M` and `50M` spans/month.
- **`google_search`** *(via isolated `deep_research_subagent`)*: Grounds public vendor licensing models, OpenTelemetry W3C TraceContext support, and self-hosted Kubernetes/OpenShift storage specs.
- **`list_syf_skills` / `load_syf_skill`**: Loads `syf-finops-tco-modeling` and `references/tco_formulas.md`.

---

## 3. Quick Setup, Testing & Deployment

```bash
# 1. Enter finops-agent and sync dependencies
cd finops-agent
uv sync

# 2. Configure environment variables
cp .env.example .env
# Populate GOOGLE_CLOUD_PROJECT, SYF_WORKSPACE_BUCKET, SYF_MCP_URL, AUTH_PROVIDER_URI

# 3. Run unit tests
uv run pytest tests/unit -v

# 4. Launch local ADK playground
uv run agents-cli playground

# 5. Deploy to Vertex AI Agent Runtime
uv run agents-cli deploy \
  --target agent-engine \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$GOOGLE_CLOUD_REGION"
```
