# Agent-to-Tools & MCP Integration Matrix (`AGENT_TO_TOOLS.md`)

Comprehensive mapping of every agent in the **AI-Driven Virtual Product Manager (VPM)** fleet (modeled for a large financial institution) to its local ADK tools, remote A2A handoffs, **FastMCP (`syf-mcp-server`)** tools, `McpToolset` `tool_filter` policies, and **GCP Agent Identity Auth Manager** configurations.

---

## 1. Master Agent-to-MCP & Tool Matrix

| Agent | Persona & Runtime Target | Local ADK & Built-In Tools *(with short description)* | Allowed `syf-mcp-server` MCP Tools *(with short description)* | External Systems & Auth Manager Config |
| :--- | :--- | :--- | :--- | :--- |
| **[`vpm-agent`](./vpm-agent)** | **Alex** — Root Virtual PM Orchestrator<br>*(Vertex AI Agent Runtime: `3255961763513958400`)* | • `consult_morgan_finops_specialist`: Delegates 3-yr vendor TCO modeling to Morgan.<br>• `consult_marcus_architecture_specialist`: Delegates CISO & curveball reviews to Marcus.<br>• `consult_devin_sdlc_specialist`: Previews or delegates SDLC tasks to Devin.<br>• `consolidate_executive_memory`: Saves approved decisions to Vertex Memory Bank.<br>• `list_syf_skills`: Lists bundled Synchrony domain skills.<br>• `load_syf_skill`: Loads a specific `SKILL.md` runbook into context. | • `list_workspace_documents`: Lists living PRD/ADR/Backlog files & live URLs.<br>• `get_workspace_document`: Reads full content of a workspace file from GCS.<br>• `patch_document_section`: Applies a redline diff to a PRD/ADR section.<br>• `create_jira_epic`: Commits Epic `SYF-5` & batch-creates 8 Sprint 1 stories.<br>• `create_jira_story`: Creates a single Gherkin story in Jira Cloud.<br>• `publish_confluence_prd`: Promotes PRD & ADR to `APPROVED` in Confluence.<br>• `create_bitbucket_branch_and_pr`: Commits code to Bitbucket & opens a PR.<br>• `sync_sdlc_ticket_blocker`: Logs a Jira blocker & patches the PRD. | • **GCS**: `vertexai-l300-capstone-syf-vpm-workspace`<br>• **Confluence Cloud**: Space `SD`<br>• **Jira Cloud**: Project `SYF` (Epic `SYF-5`)<br>• **Auth Manager**: `syf-atlassian-auth-config`, `syf-bitbucket-auth-config` |
| **[`finops-agent`](./finops-agent)** | **Morgan** — Deep Research & FinOps Analyst<br>*(Vertex AI Agent Runtime: `3546443997100736512`)* | • `google_search`: Grounds vendor pricing & infra specs via live web search.<br>• `list_syf_skills`: Lists bundled FinOps skills.<br>• `load_syf_skill`: Loads `syf-finops-tco-modeling` & TCO formulas. | • `query_vendor_cost_benchmarks`: Computes 1-yr & 3-yr TCO across Arize, Braintrust & Langfuse at 5M/50M spans. | • **GCS Seed Data**: `seed_data/eval_vendor_benchmarks.json`<br>• **Google Search Grounding**<br>• **Auth Manager**: `GcpAuthProviderScheme` (`AUTH_PROVIDER_URI`) |
| **[`arch-agent`](./arch-agent)** | **Marcus** — Enterprise Architecture & CISO<br>*(Google Cloud Run A2A: `arch-agent`)* | • `evaluate_curveball_impact`: Assesses security/schedule blast radius of curveballs.<br>• `google_search`: Grounds compliance & Envoy/OTel specs via web search.<br>• `list_syf_skills`: Lists bundled CISO/Architecture skills.<br>• `load_syf_skill`: Loads zero-trust & curveball playbook skills. | • `get_architecture_standards`: Fetches OCC, PCI-DSS 4.0, HIPAA & ROSA rules.<br>• `get_workspace_document`: Reads living PRD & ADR documents from GCS.<br>• `patch_document_section`: Redlines Section 4 of the PRD for security fixes. | • **GCS Seed Data**: `seed_data/architecture_standards.json`<br>• **Community APIs**: StackOverflow v2.3, GitHub Issues, Reddit, Google Search<br>• **Auth Manager**: `GcpAuthProviderScheme` (`AUTH_PROVIDER_URI`) |
| **[`dev-agent`](./dev-agent)** | **Devin** — Lead Platform Developer<br>*(Vertex AI Agent Runtime: `7569823371790123008`)* | • `install_and_activate_coding_skills`: Activates all 6 Synchrony `SKILL.md` rules.<br>• `fetch_assigned_sprint1_jira_stories`: Pulls assigned Sprint 1 Jira stories.<br>• `scaffold_gateway_and_envoy_mesh`: Scaffolds FastAPI gateway, UBI9 Dockerfile & K8s YAML.<br>• `scaffold_eval_suite_and_ci_pipeline`: Scaffolds 500-span eval suite, Pytest & CI pipeline.<br>• `run_security_and_latency_qa_suite`: Runs live DLP scrubbing & P95 latency QA.<br>• `commit_and_open_bitbucket_pr`: Pushes 8 files to Bitbucket PR & closes Jira stories.<br>• `deploy_and_verify_live_gateway_app`: Smoke-tests the live Cloud Run gateway API. | • `get_workspace_document`: Fetches `BACKLOG-AI-EVAL-101.json` (Sprint 1 Jira keys & custom AST specs).<br>• `create_bitbucket_branch_and_pr`: Writes 8 files to GCS, commits to Bitbucket, opens PR & marks Jira stories `Done`. | • **GCS**: `scaffolded_code/*` (8 files)<br>• **Bitbucket Cloud**: `iamsouvik/syf-eval-gateway`<br>• **Jira Cloud**: Transitions 8 Sprint 1 stories to `Done` + posts ADF comments<br>• **Live Gateway**: `/live-gateway/api/evaluate`<br>• **Auth Manager**: `syf-atlassian-auth-config`, `syf-bitbucket-auth-config` |

---

## 2. Detailed MCP & Tool Breakdown Per Agent

### 2.1 `vpm-agent` — Alex (Root Virtual PM Orchestrator)
- **Code Location**: [`vpm-agent/app/tools.py`](./vpm-agent/app/tools.py) & [`vpm-agent/app/agent.py`](./vpm-agent/app/agent.py)
- **MCP Connection Architecture**:
  - Connects to `SYF_MCP_SERVER_URL` (`https://syf-mcp-server-121190797389.us-central1.run.app/mcp`) using `McpToolset(connection_params=StreamableHTTPConnectionParams(...))` and direct stateless JSON-RPC (`tools/call`) in `_call_syf_mcp_tool_sync`.
  - Authenticated via `GcpAuthProvider` / `GcpAuthProviderScheme` and `AuthProviderCredentialsServiceClient.retrieve_credentials`.
- **Strict MCP `tool_filter` (`ALEX_ALLOWED_MCP_TOOLS`)**:
  - `list_workspace_documents()`: Lists living artifacts (`PRD-AI-EVAL-101.md`, `ADR-001-Eval-Gateway.md`, `BACKLOG-AI-EVAL-101.json`) and their live Confluence/Jira/Bitbucket URLs.
  - `get_workspace_document(document_name)`: Reads the full Markdown/JSON content of a living workspace file from GCS.
  - `patch_document_section(document_name, section_header, new_section_markdown, edit_reason, author)`: Applies a surgical "Cursor-style" unified diff (`-` / `+`) to a specific section of `PRD-AI-EVAL-101.md` or `ADR-001-Eval-Gateway.md` and syncs the draft to Confluence Cloud.
  - `create_jira_epic(epic_key, epic_title, executive_sponsor, target_sprints, approved_budget_usd)`: Updates Master Epic `SYF-5` in Jira Cloud and batch-creates the 8 Sprint 1 stories (`SYF-6+`) upon Turn 2 HITL approval.
  - `create_jira_story(...)`: Creates individual Gherkin user stories under Epic `SYF-5`.
  - `publish_confluence_prd(document_name, space_key, approved_by)`: Promotes `PRD-AI-EVAL-101.md` and `ADR-001-Eval-Gateway.md` to `APPROVED` in Confluence Cloud Space `SD`.
  - `create_bitbucket_branch_and_pr(...)`: Commits scaffolded files to Bitbucket Cloud and opens a live Pull Request.
  - `sync_sdlc_ticket_blocker(ticket_id, blocker_summary, resolution_architecture)`: Logs an engineering blocker on a Jira story and patches `PRD-AI-EVAL-101.md`.
  *(Note: `query_vendor_cost_benchmarks` and `get_architecture_standards` are intentionally excluded from Alex's `tool_filter` so Alex always delegates FinOps and CISO reviews to Morgan and Marcus.)*
- **Specialist Sub-Agent Delegation Tools**:
  - `consult_morgan_finops_specialist(research_question, monthly_spans_millions, include_gecx_50m_surge)`: Invokes **Morgan (`finops-agent`)** on Vertex AI Agent Runtime + live Google Search grounding (`MorganSearchSchema`).
  - `consult_marcus_architecture_specialist(architecture_proposal, curveball_code)`: Invokes **Marcus (`arch-agent`)** via Cloud Run A2A (`/.well-known/agent-card.json`) for Turn 1 CISO baseline audits or Turn 2 Executive Curveball blast-radius analysis.
  - `consult_devin_sdlc_specialist(action, epic_key, human_approved, ...)`: Previews or delegates SDLC backlog and scaffolding operations to **Devin (`dev-agent`)**.
  - `consolidate_executive_memory(approved_decisions_summary)`: Persists approved FinOps, CISO, and SDLC governance decisions into Vertex AI Memory Bank.

---

### 2.2 `finops-agent` — Morgan (Deep Research & FinOps Analyst)
- **Code Location**: [`finops-agent/app/tools.py`](./finops-agent/app/tools.py) & [`finops-agent/app/agent.py`](./finops-agent/app/agent.py)
- **MCP Connection Architecture**:
  - Uses `build_finops_mcp_toolset()` with `McpToolset` over `StreamableHTTPConnectionParams(url=SYF_MCP_URL)`.
  - Injects Bearer credentials via `finops_header_provider` backed by `GcpAuthProvider` and `AuthProviderCredentialsServiceClient.retrieve_credentials`.
- **Strict MCP `tool_filter`**:
  - `query_vendor_cost_benchmarks(monthly_spans_millions=5.0, include_gecx_50m_projection=True)`: Calls `syf-mcp-server` to load `seed_data/eval_vendor_benchmarks.json` from GCS and compute deterministic 1-year and 3-year TCO across **Arize AX**, **Braintrust**, and **Self-Hosted Langfuse Enterprise v3** at both `5M spans/mo` baseline and `50M spans/mo` GE-CX surge scale.
- **Local & Grounding Tools**:
  - `google_search`: Live Google Search grounding (`finops_search_grounder` sub-agent) for verifying public vendor licensing, ClickHouse storage compression, and egress pricing.
  - `list_syf_skills()` / `load_syf_skill(skill_name)`: Loads `syf-finops-tco-modeling` and `references/tco_formulas.md`.

---

### 2.3 `arch-agent` — Marcus (Enterprise Architecture & CISO Specialist)
- **Code Location**: [`arch-agent/app/tools.py`](./arch-agent/app/tools.py) & [`arch-agent/app/agent.py`](./arch-agent/app/agent.py)
- **MCP Connection Architecture**:
  - Uses `build_arch_mcp_toolset()` with `McpToolset` over `StreamableHTTPConnectionParams(url=SYF_MCP_URL)`.
  - Authenticated via `GcpAuthProviderScheme` and `arch_header_provider` (`retrieve_credentials`).
- **Strict MCP `tool_filter`**:
  - `get_architecture_standards(topic_filter="all")`: Fetches Synchrony CISO & Enterprise Architecture governance rules (`seed_data/architecture_standards.json`) covering OCC Heightened Standards, PCI-DSS v4.0 PAN/SSN scrubbing, CareCredit HIPAA BAA PHI boundaries, AWS ROSA OpenShift (`mesh.syf.bank/injected: "true"`), and Entra ID OIDC JWKS caching.
  - `get_workspace_document(document_name)`: Reads `PRD-AI-EVAL-101.md` and `ADR-001-Eval-Gateway.md`.
  - `patch_document_section(...)`: Redlines Section 4 (`API Gateway, DLP Scrubbing & Network Topology`) when an executive curveball requires architectural remediation.
- **Local & Grounding Tools**:
  - `evaluate_curveball_impact(curveball_description, baseline_sprints, baseline_story_points, baseline_annual_budget_usd)`: Queries live community APIs (StackOverflow API v2.3, GitHub Issues API, Reddit API) and Synchrony governance rules to compute the blast radius, agile velocity impact, and remediation plan for executive curveballs (`CB-1`..`CB-4` or unscripted technical prompts).
  - `google_search`: Live Google Search grounding (`arch_search_grounder` sub-agent).
  - `list_syf_skills()` / `load_syf_skill(skill_name)`: Loads `syf-zero-trust-compliance` and `syf-executive-curveball-playbook`.

---

### 2.4 `dev-agent` — Devin (Lead Platform Developer & SDLC Code Scaffolder)
- **Code Location**: [`dev-agent/app/tools.py`](./dev-agent/app/tools.py) & [`dev-agent/app/agent.py`](./dev-agent/app/agent.py)
- **Agent Topology**: Deterministic 7-Step `SequentialAgent` (`step1_skills` -> `step2_jira` -> `step3_gateway` -> `step4_eval` -> `step5_redteam` -> `step6_pr` -> `step7_deploy` -> `dev_synthesizer`).
- **MCP & Auth Manager Integration per Step**:
  1. **`install_and_activate_coding_skills`**: Scans local `dev-agent/app/skills/` and loads all 6 Synchrony `SKILL.md` specifications (`syf-rosa-gateway-scaffolding`, `syf-zero-trust-compliance`, `syf-sdlc-backlog-sync`, `syf-prd-authoring`, `syf-finops-tco-modeling`, `syf-executive-curveball-playbook`).
  2. **`fetch_assigned_sprint1_jira_stories`**: Calls `_fetch_auth_manager_credential(ATLASSIAN_AUTH_CONFIG_ID)` (`google-cloud-iamconnectorcredentials` `retrieve_credentials`), then invokes MCP tool `get_workspace_document("BACKLOG-AI-EVAL-101.json")` on `syf-mcp-server/mcp` to retrieve the 8 live Sprint 1 Jira stories (`SYF-6+`) and any `approved_custom_spec` AST requirement from Turn 1/2.
  3. **`scaffold_gateway_and_envoy_mesh`**: Builds the 4 core runtime files (`proxy_gateway.py`, `Dockerfile`, `k8s/openshift-envoy-deployment.yaml`, `templates/dashboard.html`) with dynamic AST injection for custom curveball specs.
  4. **`scaffold_eval_suite_and_ci_pipeline`**: Builds the 4 QA & CI/CD files (`eval_suite.py`, `tests/test_gateway_and_evals.py`, `bitbucket-pipelines.yml`, `requirements.txt`).
  5. **`run_security_and_latency_qa_suite`**: Runs live payload sanitization (`sanitize_telemetry_payload_live` for PCI PAN/SSN & CareCredit HIPAA MRN/ICD-10) and executes the 500-Span Golden Latency & Security QA Suite (`12/12` passed, `13.8ms` P95 latency).
  6. **`commit_and_open_bitbucket_pr`**: Calls `_fetch_auth_manager_credential(BITBUCKET_AUTH_CONFIG_ID)` (`retrieve_credentials`) and invokes `create_bitbucket_branch_and_pr` on `syf-mcp-server`, which:
     - Writes all 8 files to GCS (`gs://vertexai-l300-capstone-syf-vpm-workspace/scaffolded_code/*`).
     - Commits all 8 files to live Bitbucket Cloud (`https://bitbucket.org/iamsouvik/syf-eval-gateway` on branch `feature/SYF-5-envoy-otel-gateway`).
     - Opens a live Bitbucket Pull Request against `main`.
     - Concurrently posts ADF completion comments on all 8 Sprint 1 Jira stories + Epic `SYF-5` and transitions all 8 Jira stories to **`Done`** (`transition id = 41`).
  7. **`deploy_and_verify_live_gateway_app`**: Sends a live HTTP `POST` request to `https://syf-mcp-server-121190797389.us-central1.run.app/live-gateway/api/evaluate` and verifies HTTP `200` + live PII/HIPAA scrubbing.

---

## 3. Complete `syf-mcp-server` FastMCP Tool Catalog (`server.py`)

Hosted at `https://syf-mcp-server-121190797389.us-central1.run.app/mcp` (FastMCP Streamable HTTP):

| # | MCP Tool Name | Short Description | Primary Consumer Agent(s) | Underlying Storage / External SaaS API |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `query_vendor_cost_benchmarks` | Computes 1-yr & 3-yr vendor TCO at 5M and 50M monthly spans. | `finops-agent` (Morgan) | Reads `gs://vertexai-l300-capstone-syf-vpm-workspace/seed_data/eval_vendor_benchmarks.json`. |
| 2 | `get_architecture_standards` | Retrieves Synchrony CISO, PCI-DSS 4.0, HIPAA & ROSA policies. | `arch-agent` (Marcus) | Reads `gs://vertexai-l300-capstone-syf-vpm-workspace/seed_data/architecture_standards.json`. |
| 3 | `list_workspace_documents` | Lists all living workspace artifacts and their live SaaS URLs. | `vpm-agent` (Alex) | Lists GCS `workspace_artifacts/*` + resolves live Confluence, Jira, and Bitbucket URLs. |
| 4 | `get_workspace_document` | Fetches full Markdown or JSON content of a workspace file. | `vpm-agent` (Alex), `arch-agent` (Marcus), `dev-agent` (Devin) | Reads `PRD-AI-EVAL-101.md`, `ADR-001-Eval-Gateway.md`, or `BACKLOG-AI-EVAL-101.json` from GCS. |
| 5 | `save_workspace_document` | Overwrites a full workspace document and syncs to Confluence. | `vpm-agent` (Alex) | Writes to GCS `workspace_artifacts/*` and updates **Atlassian Confluence Cloud**. |
| 6 | `patch_document_section` | Applies a surgical redline diff to a Markdown section. | `vpm-agent` (Alex), `arch-agent` (Marcus) | Computes `difflib.unified_diff`, updates GCS, and pushes a new version to **Confluence Cloud** (`PUT /wiki/rest/api/content/{id}`). |
| 7 | `create_jira_epic` | Updates Master Epic `SYF-5` and batch-creates 8 Sprint 1 stories. | `vpm-agent` (Alex) | Updates `SYF-5` and concurrently creates 8 stories (`SYF-6+`) in **Atlassian Jira Cloud** (`POST /rest/api/3/issue`). |
| 8 | `create_jira_story` | Creates a single Gherkin user story under Epic `SYF-5`. | `vpm-agent` (Alex) | Creates an issue in **Atlassian Jira Cloud** under Parent Epic `SYF-5`. |
| 9 | `publish_confluence_prd` | Promotes PRD and ADR pages to `APPROVED` status. | `vpm-agent` (Alex) | Updates page status and metadata in **Atlassian Confluence Cloud** Space `SD`. |
| 10 | `create_bitbucket_branch_and_pr` | Commits 8 files to Bitbucket, opens PR & marks Jira stories `Done`. | `dev-agent` (Devin), `vpm-agent` (Alex) | Writes to GCS (`scaffolded_code/*`), commits to **Bitbucket Cloud** (`POST .../src`), opens PR (`POST .../pullrequests`), and transitions 8 Jira stories to **`Done`**. |
| 11 | `sync_sdlc_ticket_blocker` | Records a story blocker in the backlog and patches the PRD. | `vpm-agent` (Alex) | Updates `BACKLOG-AI-EVAL-101.json` in GCS and patches Section 4 of `PRD-AI-EVAL-101.md`. |
