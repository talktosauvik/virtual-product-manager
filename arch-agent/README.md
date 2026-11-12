# `arch-agent` — Marcus (CISO & Enterprise Architecture Specialist)

**Marcus (`arch-agent`)** is the Chief Information Security Officer (CISO) and Enterprise Architecture agent (modeled for a large financial institution). Built on **Google ADK 2.0 (`Workflow` Graph + `JoinNode`)** and deployed on **Google Cloud Run** as a remote **Agent-to-Agent (A2A) JSON-RPC** server (`/.well-known/agent-card.json`), Marcus enforces OCC Heightened Standards (`12 CFR Part 30`), PCI-DSS v4.0 (`PAN`/`SSN`), CareCredit HIPAA BAA (`MRN`/`ICD-10`), AWS ROSA OpenShift Envoy Service Mesh (`mesh.syf.bank/injected: "true"`, mTLS 1.3), and dynamic Executive Curveball blast-radius analysis.

---

## 1. Architecture & Runtime Profile

- **Framework**: Google ADK 2.0 (`Workflow` graph with `(zero_trust_dlp_auditor, mesh_latency_auditor)` parallel fan-out → `arch_join = JoinNode` + dynamic `@node(rerun_on_resume=True)` curveball evaluator)
- **Model**: `MODEL=gemini-3-flash-preview` (`THINKING_LEVEL=low`, `GOOGLE_CLOUD_LOCATION=global`)
- **Deployment Target**: Google Cloud Run (`deployment_target: cloud_run`, `is_a2a: true`)
- **A2A Discovery Endpoint**: `<ARCH_AGENT_URL>/.well-known/agent-card.json`
- **Authentication**: Uses dedicated IAM Service Account + **GCP Agent Identity Auth Manager** (`GcpAuthProviderScheme` + `retrieve_credentials`).

---

## 2. Core Tools (`app/tools.py` & `app/agent.py`)

- **`get_architecture_standards`** *(via `syf-mcp-server` `McpToolset`)*: Retrieves official enterprise CISO & CTO governance standards (`seed_data/architecture_standards.json` in GCS).
- **`get_workspace_document` / `patch_document_section`** *(via `syf-mcp-server`)*: Reads living `PRD-AI-EVAL-101.md` / `ADR-001-Eval-Gateway.md` and applies surgical architectural redlines.
- **`evaluate_curveball_impact`**: Evaluates scripted (`CB-1`..`CB-4`) and unscripted developer/executive curveballs by querying StackOverflow API v2.3, GitHub Issues API, Reddit API, and enterprise governance rules to compute blast radius, agile sprint savings, and remediation controls.
- **`list_syf_skills` / `load_syf_skill`**: Loads `syf-zero-trust-compliance` and `syf-executive-curveball-playbook`.

---

## 3. Quick Setup, Testing & Deployment

```bash
# 1. Enter arch-agent and sync dependencies
cd arch-agent
uv sync

# 2. Configure environment variables
cp .env.example .env
# Populate GOOGLE_CLOUD_PROJECT, SYF_WORKSPACE_BUCKET, SYF_MCP_URL, AUTH_PROVIDER_URI

# 3. Run unit tests
uv run pytest tests/unit -v

# 4. Launch local ADK playground
uv run agents-cli playground

# 5. Deploy to Google Cloud Run (Remote A2A Server)
uv run agents-cli deploy \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$GOOGLE_CLOUD_REGION"
```
