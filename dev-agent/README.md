# `dev-agent` — Devin (Lead Cloud & IaC Engineer)

**Devin (`dev-agent`)** is the autonomous Lead Cloud & IaC Engineer (modeled for a large financial institution). Built on **Google ADK 2.0 (`Workflow` Graph, `FunctionNode` with `RetryConfig`, and `JoinNode` fan-out/fan-in diamonds)**, deployed on **Vertex AI Agent Runtime (`ReasoningEngine`)**, and registered in **Gemini Enterprise**, Devin executes a 7-step Sprint 1 engineering pipeline that pulls assigned Jira stories (`SYF-5`), activates 6 enterprise engineering skills, scaffolds an 8-file Envoy/OpenTelemetry DLP Gateway repository (injecting any custom Turn 2 curveball AST features), runs a 2-iteration Security/DLP & 500-Span Golden Latency QA suite, commits all 8 files to **Bitbucket Cloud** (`syf-eval-gateway`), opens a live Pull Request, transitions all 8 Jira stories to **`DONE`**, and smoke-tests the live Cloud Run gateway.

---

## 1. Architecture & Runtime Profile

- **Framework**: Google ADK 2.0 (`google.adk.workflow.Workflow`, `FunctionNode`, `JoinNode`, `RetryConfig`) streaming live `function_call` / `function_response` events (`✅` checkmarks in Gemini Enterprise)
- **Model**: `MODEL=gemini-3-flash-preview` (`thinking_level="LOW"`, `GOOGLE_CLOUD_LOCATION=global`)
- **Deployment Target**: Vertex AI Agent Runtime (`deployment_target: agent_runtime`, `is_a2a: true`)
- **Authentication**: Uses Lab 3 **GCP Agent Identity Auth Manager** (`AuthenticatedFunctionTool` + `GcpAuthProviderScheme` + `AuthProviderCredentialsServiceClient`) with zero hardcoded API keys.

---

## 2. 7-Step Autonomous Execution Pipeline (`app/agent.py` & `app/tools.py`)

1. **`install_and_activate_coding_skills`**: Discovers and loads all 6 enterprise `SKILL.md` specifications (`syf-rosa-gateway-scaffolding`, `syf-zero-trust-compliance`, `syf-sdlc-backlog-sync`, etc.).
2. **`fetch_assigned_sprint1_jira_stories`**: Queries `BACKLOG-AI-EVAL-101.json` via `syf-mcp-server` for the 8 assigned Sprint 1 Jira stories (`SYF-6+`) and any approved custom runtime specification.
3. **`scaffold_gateway_and_envoy_mesh`** *(Parallel Branch A)*: Generates `proxy_gateway.py`, `Dockerfile` (Red Hat UBI9 non-root `USER 1001`), `k8s/openshift-envoy-deployment.yaml` (`mesh.syf.bank/injected: "true"`), `templates/dashboard.html`, and `requirements.txt`.
4. **`scaffold_eval_suite_and_ci_pipeline`** *(Parallel Branch B)*: Generates `eval_suite.py` (500-span golden benchmark), `tests/test_gateway_and_evals.py` (12 Pytest checks), and `bitbucket-pipelines.yml`.
5. **`run_security_and_latency_qa_suite`**: Executes the 2-iteration Security/DLP & Latency self-correction loop (`48.6ms -> 13.8ms` P95 via 300s Entra ID JWKS cache; `12/12` Pytest passed; `100%` PAN/SSN/MRN/ICD-10 recall; `0` `eval()` calls).
6. **`commit_and_open_bitbucket_pr`** *(Parallel Delivery Branch A)*: Invokes `create_bitbucket_branch_and_pr` on `syf-mcp-server` to save all 8 files to GCS (`scaffolded_code/*`), commit to Bitbucket Cloud (`<BITBUCKET_WORKSPACE>/syf-eval-gateway` branch `feature/SYF-5-envoy-otel-gateway`), open a live Pull Request, post completion comments, and transition all 8 Sprint 1 Jira stories to **`DONE`**.
7. **`deploy_and_verify_live_gateway_app`** *(Parallel Delivery Branch B)*: Executes an end-to-end HTTP `POST /live-gateway/api/evaluate` smoke test verifying live PII/PCI/HIPAA redaction.

---

## 3. Quick Setup, Testing & Deployment

```bash
# 1. Enter dev-agent and sync dependencies
cd dev-agent
uv sync

# 2. Configure environment variables
cp .env.example .env
# Populate GOOGLE_CLOUD_PROJECT, SYF_MCP_URL, LIVE_GATEWAY_URL, BITBUCKET_WORKSPACE, BITBUCKET_REPO_SLUG=syf-eval-gateway, JIRA_PROJECT_KEY=SYF, JIRA_EPIC_KEY=SYF-5

# 3. Run unit & full 7-step workflow tests
uv run pytest tests/unit/test_dev_agent_workflow.py -v

# 4. Launch local ADK playground
uv run agents-cli playground

# 5. Deploy to Vertex AI Agent Runtime
uv run agents-cli deploy \
  --target agent-engine \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$GOOGLE_CLOUD_REGION"

# 6. Register Devin in Gemini Enterprise
DEV_ENGINE_ID="$(jq -r .remote_agent_runtime_id deployment_metadata.json)"
uv run agents-cli publish gemini \
  --project-id "$GOOGLE_CLOUD_PROJECT" \
  --app-id "$GEMINI_ENTERPRISE_APP_ID" \
  --location global \
  --agent-engine-id "$DEV_ENGINE_ID" \
  --display-name "Devin - Lead Platform Developer" \
  --description "Autonomous Lead Platform Developer & SDLC Code Scaffolder"
```
