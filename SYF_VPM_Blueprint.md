# Synchrony Financial (SYF) — Virtual Product Manager (VPM) Architecture Critique & Implementation Blueprint (v2)

**References Analyzed:**
- **Account Strategy**: `AI Strategy_Synchrony Financial.pdf`
- **System Specification Document (SSD)**: `syf_virtual_pm_ssd.pdf`
- **FSR Field Notes**: *"Mimic Cursor"*, *"Pull in Antigravity"*, and *"Integrate with their SDLC"* (4-stage continuous product lifecycle loop)
- **Identity & Auth Reference**: `lab 3.pdf` (`APEX013: Agent Identity Foundations — Auth Manager, SPIFFE & Service Account Identities`)
- **ADK & CLI Skills**: `google-agents-cli-workflow`, `google-agents-cli-adk-code`, `google-agents-cli-scaffold`, `google-agents-cli-eval`, `google-agents-cli-deploy`, `google-agents-cli-publish`, `google-agents-cli-observability`

**Scope & Front-End Touchpoint:**
- **Master Agent Registered in Gemini Enterprise (GE) App**: We will register the master orchestrator (`vpm-agent` / Alex, running on **Agent Runtime**) directly into your **Gemini Enterprise App** using `agents-cli publish gemini --registration-type adk` so you have the full Gemini Enterprise UI front-end to converse with Alex.
- **Colleague Handoff for Gateway/Model Armor**: All deployed agents will also expose standards-compliant **A2A AgentCard URLs** (`/a2a/app/.well-known/agent-card.json`) so your colleague can take those cards and attach Agent Registry, Agent Gateway, and edge Model Armor policies in a separate governance project.

---

## 1. Feedback on the Current SSD (`syf_virtual_pm_ssd.pdf`)

### Executive & Narrative Assessment
The SSD is exceptionally well-aligned with **Dan Weis's (VP of AI Innovation)** and **Nimrod Barak's (Chief AI Officer)** executive priorities from `AI Strategy_Synchrony Financial.pdf`:
1. **High-Impact Executive Hook**: Uses a real decision Dan Weis faces—evaluating **Arize vs. Braintrust vs. Langfuse** at 5M monthly spans—and proves **$109,000/yr TCO savings** via self-hosted Langfuse on OpenShift (ROSA).
2. **Multi-Agent Tension (Cost vs. Security)**: Pits **Morgan (FinOps)** against **Marcus (Enterprise Architect)** enforcing zero-egress PCI-DSS compliance and Microsoft Entra ID mTLS.
3. **Resilience Under Live Executive Testing**: Explicitly designs around Dan's **"Wicked Curveball"** (mid-session Kong Gateway deprecation -> internal service mesh) and a **Human-in-the-Loop (HITL)** approval gate before mutating Jira/Confluence.
4. **Decreasing Marginal Cost Thesis**: Closes with **Vertex AI Memory Bank** consolidation (`user_id="dan_weis_ai_innovation"`), proving how organizational context carries forward across sessions and future role-based AI employees.

### Technical & Code Deficiencies in the SSD (Must Fix for Prototype)
While the narrative and UI contract (Sections 1–6) are strong, **the code in Sections 7, 9, 10, 11, and 12 will fail at runtime** due to hallucinated ADK imports, LangGraph syntax mixed into ADK 2.0, hardcoded node outputs, and a security flaw:

| SSD Section | Technical Defect in SSD | Fix Applied in Our Implementation Blueprint |
| :--- | :--- | :--- |
| **Sec 9: Sub-Agents Never Invoked** | `finops_agent`, `architecture_agent`, and `dev_agent` are defined as `Agent(...)`, but `finops_analysis_node`, `architecture_review_node`, `multi_agent_debate_node`, `handle_curveball_node`, and `dev_agent_scaffold_node` **never call the agents**—they just return hardcoded strings! | Replace static dict returns with **real LLM agent invocations and A2A `RemoteA2aAgent` calls** backed by deterministic tools. If Dan throws an unscripted curveball live, real agents will reason over it rather than returning static text. |
| **Sec 9: Invalid ADK 2.0 `Workflow` API** | Uses LangGraph-style `async def node(state: Dict) -> Dict` and `(node, {"ROUTE": target}, router_fn)` edges. | Use native ADK 2.0 orchestration: stateful `LlmAgent` coordinator + `ParallelAgent` / `SequentialAgent` / `RemoteA2aAgent` + `ToolContext`. |
| **Sec 9: Fake HITL Gate** | `prompt_for_approval_node` sets `state["awaiting_human_approval"] = True`, which does **not** pause execution in ADK. | Use ADK's native HITL confirmation (`FunctionTool(..., require_confirmation=True)` / explicit approval gate), guaranteeing zero Jira/Confluence writes until Dan approves. |
| **Sec 9: Non-Existent `McpToolClient` & Auth** | Imports `from google.adk.tools import McpToolClient` (does not exist) and hardcodes localhost SSE URLs without authentication. | Follow `lab 3.pdf` (`APEX013`): use `McpToolset` with `StreamableHTTPConnectionParams`, `CredentialManager.register_auth_provider(GcpAuthProvider())`, `GcpAuthProviderScheme`, and `header_provider` (or `AuthenticatedFunctionTool`). |
| **Sec 9: Hallucinated Memory Bank Methods** | Calls `memory_service.search_memories()` and `memory_service.add_memory(metadata=...)` directly with invalid signatures. | Use ADK's native `PreloadMemoryTool()` and `after_agent_callback=generate_memories_callback` (`await callback_context.add_session_to_memory()`), backed by `VertexAiMemoryBankService` (`lab 3.pdf`). |
| **Sec 10.1: Critical RCE in `proxy_gateway.py`** | `sanitize_telemetry_payload` executes `return eval(sanitized_str)` on incoming untrusted JSON telemetry payloads. | Replace `eval()` with `json.loads(CARD_REGEX.sub(..., SSN_REGEX.sub(..., json.dumps(data))))` so Devin generates genuinely hardened code that passes CISO inspection. |
| **Sec 11: Invalid `eval_config.yaml` Schema** | Uses `eval_set_id:`, `evaluators:`, `type: tool_call_match` (not valid in `agents-cli eval`). | Use the canonical `google-agents-cli-eval` schema: `metrics_to_run:` (`multi_turn_task_success`, `multi_turn_trajectory_quality`, `multi_turn_tool_use_quality`, `safety`) + `custom_metrics:` (`prompt_template` & `custom_function`). |
| **Sec 12: Manual `mkdir` Instead of Scaffold** | Runs `mkdir -p` and manual `uv pip install`, losing A2A `AgentCardBuilder` wiring, `fast_api_app.py`, and deployment manifests. | Use `agents-cli scaffold create <name> --agent adk --deployment-target <agent_runtime\|cloud_run> --prototype`. |

---

## 2. Augmenting the SSD with the FSR Notes (GCS Workspace, Mock Antigravity Skills, & SDLC Sync)

The FSR notes introduce three pillars—**"Mimic Cursor"**, **"Pull in Antigravity"**, and **"Integrate with their SDLC (Continuous Loop)"**. Here is the exact storage and execution architecture for each:

### A. Shared GCS Bucket Architecture (`gs://${PROJECT_ID}-syf-vpm-workspace/`)
To ensure all Cloud Run services (`syf-mcp-server`, `arch-agent`, `dev-agent`) and Agent Runtime agents (`vpm-agent`, `finops-agent`) share a single source of truth—and so you can visually inspect files changing live in the Google Cloud Console during the demo—we store all seed data, living "Cursor" documents, mock Antigravity skills, and scaffolded code in a central **Google Cloud Storage (GCS) Bucket**:

```text
gs://${PROJECT_ID}-syf-vpm-workspace/
├── seed_data/                           # Pre-populated enterprise reference data
│   ├── eval_vendor_benchmarks.json      # Arize, Braintrust, Langfuse unit economics & scaling rules
│   ├── architecture_standards.json      # PCI-DSS, CareCredit HIPAA, Entra ID, Kong Q1 deprecation, ROSA/Cloud Run
│   └── jira_seed_templates.json         # Jira project keys, SYF squad rosters, Gherkin templates, Bitbucket repos
├── skills/                              # 6 Synchrony Mock Antigravity SKILL.md files (also bundled in agent repos)
│   ├── syf-agentic-workflow/SKILL.md
│   ├── syf-prd-finops-blueprint/SKILL.md
│   ├── syf-zero-trust-architecture/SKILL.md
│   ├── syf-rosa-service-scaffold/SKILL.md
│   ├── syf-sdlc-jira-bitbucket/SKILL.md
│   └── syf-otel-eval-governance/SKILL.md
├── workspace_artifacts/                 # "Cursor-Style" Living Product Files (versioned v1, v2, ...)
│   ├── PRD-AI-EVAL-101.md               # Living Product Requirements Document (with section anchors)
│   ├── ADR-001-Eval-Gateway.md          # Living Architecture Decision Record
│   └── BACKLOG-AI-EVAL-101.json         # Live Jira Epics, Stories, Blocker statuses & Bitbucket branch links
└── scaffolded_code/                     # Generated by Devin (dev-agent) upon PRD/Backlog approval
    ├── Dockerfile                       # Hardened Red Hat UBI9 Python 3.12 container
    ├── proxy_gateway.py                 # FastAPI + OTel W3C TraceContext + safe regex PII/PHI scrubber
    ├── k8s_deployment.yaml              # OpenShift/ROSA deployment with Service Mesh sidecar injection
    └── requirements.txt
```

### B. How We "Mimic Cursor" (Multi-File Context & Surgical Inline Editing)
* **Where the Files Live**: Stored in `gs://${PROJECT_ID}-syf-vpm-workspace/workspace_artifacts/` (and registered as ADK Artifacts via `GcsArtifactService` + mirrored locally in `syf-mcp-server`).
* **How Inline Editing Works in Gemini Enterprise Chat**:
  1. When Alex (`vpm-agent`) drafts `PRD-AI-EVAL-101.md` (`v1.0`), the document is structured with clean Markdown section headers (`## 1. Executive Summary`, `## 2. FinOps TCO Analysis`, `## 3. Target Architecture`, `## 4. Security, Ingress & Compliance`, `## 5. Rollout & Sprint Plan`).
  2. When Dan Weis highlights a requirement in chat—e.g., *"Rewrite Section 4 of the PRD to comply with our CareCredit HIPAA privacy rules"* or throws the Kong Gateway deprecation curveball—Alex calls the MCP tool `patch_document_section(document_name="PRD-AI-EVAL-101.md", section_header="## 4. Security, Ingress & Compliance", updated_content=..., reason=...)`.
  3. The tool reads `PRD-AI-EVAL-101.md` from the GCS bucket, surgically splices **only** Section 4, writes `v1.1` back to GCS, and returns a **Cursor-Style Unified Diff (`- removed` / `+ added` lines)** plus the updated GCS URI so Dan sees the exact surgical edit inline in Gemini Enterprise!

### C. How We "Pull in Antigravity" (6 Mock-Up Synchrony `SKILL.md` Skills)
We will create **6 Synchrony-specific mock-up `SKILL.md` files** modeled directly after the 6 `google-agents-cli` skills, stored both in `vpm-agent/app/skills/` (for fast local/container access) and in `gs://${PROJECT_ID}-syf-vpm-workspace/skills/`:

| # | Mock Antigravity Skill Name | Mirrors `agents-cli` Skill | Purpose in the Synchrony VPM Demo |
| :--- | :--- | :--- | :--- |
| **1** | `syf-agentic-workflow` | `google-agents-cli-workflow` | Defines Synchrony's 4-stage Agentic PM loop: Inception -> Cursor-style PRD/ADR drafting -> HITL Approval Gate -> Jira/Bitbucket SDLC translation & Continuous Blocker Sync. |
| **2** | `syf-prd-finops-blueprint` | `google-agents-cli-adk-code` | Synchrony's official PRD markdown schema, FinOps TCO formula rules (base license + per-million span cost + ROSA compute overhead), and executive summary card structure. |
| **3** | `syf-zero-trust-architecture` | `google-agents-cli-deploy` | Synchrony's enterprise architecture guardrails: PCI-DSS zero-egress, CareCredit HIPAA PHI redaction, Microsoft Entra ID mTLS/JWKS, Kong Q1 deprecation -> Envoy Service Mesh, and ROSA vs. Cloud Run Private Subnets. |
| **4** | `syf-rosa-service-scaffold` | `google-agents-cli-scaffold` | Golden engineering patterns used by Devin (`dev-agent`) to scaffold Red Hat UBI9 `Dockerfile`, FastAPI `proxy_gateway.py`, and OpenShift `k8s_deployment.yaml`. |
| **5** | `syf-sdlc-jira-bitbucket` | `google-agents-cli-publish` | Rules for decomposing PRDs into Jira Epics (`AI-EVAL-101`), Gherkin User Stories, SYF squad assignments (`Platform-Mesh-Squad`, `AI-FinOps-Squad`), Bitbucket feature branches, and blocker impact sync. |
| **6** | `syf-otel-eval-governance` | `google-agents-cli-eval` & `observability` | OpenTelemetry W3C `TraceContext` header standards, `<25ms` P95 proxy latency budgets, and LLM-as-judge evaluation rubrics. |

* **How Agents Use Them**: Alex and Devin have `list_antigravity_skills()` and `activate_antigravity_skill(skill_name)` tools. When you expand the tool call trace in Gemini Enterprise, you will see Alex dynamically load `syf-prd-finops-blueprint` and `syf-zero-trust-architecture` on demand!

### D. How We Utilize Vertex AI Memory Bank for Long-Term Context Awareness
We will use **managed Vertex AI Memory Bank (`VertexAiMemoryBankService`)** on Agent Runtime (matching `lab 3.pdf` pages 29–31):
1. **Automatic Pre-Turn Recall (`PreloadMemoryTool`)**: `vpm-agent` includes `PreloadMemoryTool()` in `tools=[..., PreloadMemoryTool()]`. At the beginning of every user turn in Gemini Enterprise, ADK queries the Agent Runtime's Vertex AI Memory Bank for memories scoped to the user and injects them into the system prompt automatically.
2. **Automatic Post-Turn Consolidation (`after_agent_callback`)**: `vpm-agent` registers `after_agent_callback=generate_memories_callback` which executes `await callback_context.add_session_to_memory()`. Whenever Dan states a strategic preference, throws a curveball (e.g., Kong deprecation in Q1), or approves an ADR, Vertex AI Memory Bank extracts and persists those facts asynchronously.
3. **Explicit Memory Inspection / Seed Tool**: We also include a `save_executive_memory_note` / `recall_executive_memory_notes` helper backed by GCS + Memory Bank so during the demo Alex can explicitly display the **`memory_consolidation_card`** showing the exact facts persisted for future sessions and other AI employees (proving Dan Weis's "Decreasing Marginal Cost" thesis).

---

## 3. What's Good vs. What Can Be Improved & Optimized (Plus Dan Weis's Curveball Matrix)

### What's Good vs. What We Will Optimize

| Dimension | What's Good in Current Design (Preserve) | What Can Be Improved & Optimized (Upgrade) |
| :--- | :--- | :--- |
| **Orchestration Topology** | Clear 8-step executive story (`S1` Intake -> `S2` FinOps -> `S3` Arch Debate -> `S4` Curveball -> `S5` HITL -> `S6` Jira/Confluence -> `S7` Code Gen -> `S8` Memory). | **Conversational Coordinator + A2A Sub-Agents**: Pure static graph nodes break if Dan asks an unscripted follow-up question in Gemini Enterprise. Making **Alex (`vpm-agent`)** an `LlmAgent` orchestrator on **Agent Runtime** that delegates to **Morgan**, **Marcus**, and **Devin** via **A2A (`RemoteA2aAgent`)** supports both the 8-step flow *and* free-form multi-turn dialogue. |
| **Security & Credentials** | Conceptually highlights zero-trust identity and no hardcoded keys. | **Lab 3 (`APEX013`) Agent Identity Auth Manager**: Implement real **Agent Identity Auth Manager** providers (`gcloud alpha agent-identity auth-providers`): **SPIFFE Principal** on Agent Runtime (`vpm-agent`, `finops-agent`) and **Service Account Identity** on Cloud Run (`arch-agent`, `dev-agent`) resolving credentials via `GcpAuthProvider` + `GcpAuthProviderScheme`. |
| **FinOps Benchmarking** | Compares Arize ($185k), Braintrust ($135k), and Langfuse ($76k) at 5M spans/mo. | **Dynamic TCO Formula Engine**: Make `query_vendor_cost_benchmarks` dynamically compute `licensing_base + (monthly_spans_millions * 12 * span_cost_per_million) + infra_compute_overhead` from the GCS seed file so Dan can test *any* span volume (e.g., 50M spans for 9,000 GECX agents!). |
| **Google Search Grounding** | Uses `google_search` in `deep_research_agent` for live vendor/CVE lookup. | **Sub-Agent Isolation for `google_search`**: Mixing `google_search` with `FunctionTool`s in the same `Agent` disables Automatic Function Calling (AFC). Within `finops-agent`, we isolate `deep_research_analyst` (`tools=[google_search]`) from `finops_tco_analyst` (`tools=[McpToolset(...)]`) and combine them via `AgentTool`. |

### The "Wicked Curveball" Matrix (Preparing for Dan Weis's Live Test)
We will bake **5 high-probability Synchrony curveballs** into our GCS seed data (`architecture_standards.json` & `eval_vendor_benchmarks.json`) and `evaluate_curveball_impact` tool so Alex and Marcus handle any of them live without hallucinating:

| # | Curveball Scenario Dan Might Throw | Trigger / Constraint | Deterministic Impact & Multi-Agent Adaptation |
| :--- | :--- | :--- | :--- |
| **CB-1** *(SSD Default)* | **Kong API Gateway Deprecation in Q1** | *"Stop. Architecture is deprecating Kong Gateway in Q1 and moving all API traffic to an internal Envoy service mesh."* | • **Marcus (Arch)**: Decouples Kong ingress plugins; shifts Entra ID JWT validation & mTLS termination to Envoy Service Mesh sidecar (`mesh.syf.bank/injected: "true"`).<br>• **Alex (VPM)**: Recalculates roadmap (**+2 sprints**, 6 -> 8 sprints, +$32k engineering cost); surgically patches PRD Section 4 & ADR-001 in GCS. |
| **CB-2** *(FinOps Scale)* | **10x Span Volume Surge (GECX 9,000 Agents)** | *"What if we expand scope to include our 9,000 GECX contact center agents—jumping from 5M to 50M spans/month?"* | • **Morgan (FinOps)**: Re-runs `query_vendor_cost_benchmarks(monthly_eval_spans=50_000_000)`. Arize TCO explodes to **$1,285,000/yr**; Braintrust to **$960,000/yr**; Langfuse Self-Hosted scales to **$156,000/yr** ($36k license + $120k ClickHouse cluster), increasing annual savings to **$1,129,000/yr**!<br>• **Marcus & Alex**: Adds **+1 sprint** (8pt story) for ClickHouse multi-shard replication on ROSA. |
| **CB-3** *(CISO / HIPAA)* | **CareCredit Medical Financing (HIPAA + PCI-DSS)** | *"CISO Kara Schimmeck says CareCredit healthcare chats will use this gateway. We now need HIPAA PHI + PCI-DSS redaction before ClickHouse storage."* | • **Marcus (Arch)**: Mandates inline PHI/PII tokenization (`SSN`, `CREDIT_CARD`, `MEDICAL_RECORD_NUMBER`, `ICD10_CODE`) inside the FastAPI OTel interceptor.<br>• **Devin (Dev)**: Adds HIPAA regex/DLP scrubbers to `proxy_gateway.py` (`<25ms` P95 latency SLA). Adds **+1 sprint**. |
| **CB-4** *(Multi-Cloud Pivot)* | **ROSA Capacity Freeze -> Deploy Proxy on Cloud Run** | *"Our AWS ROSA OpenShift cluster capacity is frozen until Q3. Can we host the evaluation proxy on Google Cloud Run Private Subnets instead?"* | • **Marcus (Arch)**: Validates against `architecture_standards.json` (`approved_runtimes` includes `"Google Cloud Run Private Subnets"` with PSC interconnect to ClickHouse).<br>• **Devin (Dev)**: Pivots scaffold output from OpenShift Route to Cloud Run `service.yaml` with `INGRESS_TRAFFIC_INTERNAL_ONLY`, **saving 1 sprint** (-1 sprint, 6 -> 5 sprints)! |
| **CB-5** *(FSR SDLC Blocker)* | **Mid-Sprint Developer Ticket Blocker (Entra ID JWKS Latency)** | *"A developer just flagged a blocker on AI-STORY-102: synchronous Entra ID token introspection is adding 180ms latency, violating our 25ms SLA."* | • **Alex & Marcus**: Runs `sync_sdlc_ticket_blocker`; updates ADR-001 & PRD inline to switch from synchronous token introspection to **local JWKS public-key caching (5-min TTL)** in the sidecar, reducing auth overhead to `<2ms`. |

---

## 4. Comprehensive Step-by-Step Implementation & Deployment Plan

### Target Hybrid Topology
- **Gemini Enterprise (GE) App Front-End**: Connected natively (`--registration-type adk`) to `vpm-agent` on Agent Runtime.
- **Agent Runtime (2 Stateful / Identity-Governed Agents)**:
  1. **`vpm-agent` (Alex — Root Virtual PM Orchestrator)**: Coordinates specialists via A2A, loads Antigravity `SKILL.md` files, manages Cursor-style living PRD/ADR files in GCS, enforces HITL approval before Jira/Confluence writes, and consolidates long-term context into **Vertex AI Memory Bank**.
  2. **`finops-agent` (Morgan — Deep Research & FinOps Analyst)**: Runs `google_search` grounding + FinOps TCO calculations via `syf-mcp-server`, authenticated with its **Agent Runtime SPIFFE principal** via **Agent Identity Auth Manager**.
- **Cloud Run (2 Specialist Agents + 1 Enterprise FastMCP Server)**:
  3. **`arch-agent` (Marcus — Enterprise Architecture Specialist)**: Evaluates PCI-DSS/HIPAA/Entra ID standards and Curveball blast radius via `syf-mcp-server`, authenticated with its **Cloud Run Service Account** via **Agent Identity Auth Manager**.
  4. **`dev-agent` (Devin — Developer & SDLC Scaffolder)**: Generates hardened `proxy_gateway.py`, `Dockerfile`, and `k8s_deployment.yaml` into GCS (`gs://${PROJECT_ID}-syf-vpm-workspace/scaffolded_code/`) and maps Jira stories to Bitbucket branches/PRs.
  5. **`syf-mcp-server` (Synchrony Enterprise FastMCP Server)**: Stateless Cloud Run container serving `/mcp` (Streamable HTTP) backed by the shared GCS bucket `gs://${PROJECT_ID}-syf-vpm-workspace/`.

---

### Step-by-Step Build & Deployment Phases

#### Phase 1: GCP Environment, GCS Workspace Bucket & Agent Identity Auth Manager (Lab 3)
1. **Enable Required GCP APIs**:
   - `aiplatform.googleapis.com`, `run.googleapis.com`, `cloudbuild.googleapis.com`, `storage.googleapis.com`, `discoveryengine.googleapis.com`, `agentidentity.googleapis.com`, `agentidentitycredentials.googleapis.com`, `iamcredentials.googleapis.com`, `sts.googleapis.com`.
2. **Create & Seed the Shared GCS Workspace Bucket (`gs://${PROJECT_ID}-syf-vpm-workspace`)**:
   - Create the bucket and upload:
     - `seed_data/eval_vendor_benchmarks.json`
     - `seed_data/architecture_standards.json`
     - `seed_data/jira_seed_templates.json`
     - `skills/` (all 6 Synchrony Antigravity `SKILL.md` files)
3. **Create the Auth Provider in Agent Identity Auth Manager** (`lab 3.pdf` Task 2):
   - Create API-key auth provider `syf-mcp-auth-provider` in `agentidentity.googleapis.com` holding `SYF_MCP_API_KEY`.
   - Grant `roles/agentidentity.user` on `syf-mcp-auth-provider` to your developer user email for local testing.

#### Phase 2: Build & Deploy `syf-mcp-server` on Cloud Run
1. **Implement `syf-mcp-server/server.py` (FastMCP Streamable HTTP on `/mcp`, port `8080`)**:
   - Reads/writes directly to `gs://${PROJECT_ID}-syf-vpm-workspace/` (with local file fallback for offline testing).
   - **Tools**:
     - `query_vendor_cost_benchmarks(monthly_eval_spans, deployment_preference)`
     - `get_architecture_standards(domain_filter)`
     - `list_workspace_documents()` & `get_workspace_document(document_name)`
     - `save_workspace_document(document_name, content, author)`
     - `patch_document_section(document_name, section_header, new_section_markdown, edit_reason)` -> returns Cursor-style unified diff (`-` / `+`) and updates version in GCS!
     - `create_jira_epic(...)`, `create_jira_story(...)`, `publish_confluence_prd(...)`
     - `create_bitbucket_branch_and_pr(story_key, repo_name, branch_name, files_committed)`
     - `sync_sdlc_ticket_blocker(ticket_id, blocker_description)`
2. **Deploy `syf-mcp-server` to Cloud Run** (`gcloud run deploy syf-mcp-server ...`) and grant its service account `roles/storage.objectAdmin` on `gs://${PROJECT_ID}-syf-vpm-workspace`.

#### Phase 3: Scaffold, Build & Deploy Cloud Run Specialist Agents (`arch-agent` & `dev-agent`)
1. **Scaffold via `agents-cli`**:
   ```bash
   agents-cli scaffold create arch-agent --agent adk --deployment-target cloud_run --region $REGION --prototype --agent-guidance-filename GEMINI.md
   agents-cli scaffold create dev-agent --agent adk --deployment-target cloud_run --region $REGION --prototype --agent-guidance-filename GEMINI.md
   ```
2. **Build `arch-agent` (Marcus)**:
   - Wire `CredentialManager.register_auth_provider(GcpAuthProvider())` + `GcpAuthProviderScheme(name=SYF_MCP_AUTH_PROVIDER_URI)` + `McpToolset` (`StreamableHTTPConnectionParams(url=SYF_MCP_URL)`).
   - Add `evaluate_curveball_impact` tool covering all 5 Curveball scenarios (`CB-1` through `CB-5`) and `activate_antigravity_skill("syf-zero-trust-architecture")`.
3. **Build `dev-agent` (Devin)**:
   - Wire `McpToolset` via `GcpAuthProviderScheme`.
   - Add `scaffold_evaluation_gateway` tool (loads `syf-rosa-service-scaffold/SKILL.md`, generates hardened `Dockerfile`, RCE-free `proxy_gateway.py`, `k8s_deployment.yaml`, saves them to `gs://${PROJECT_ID}-syf-vpm-workspace/scaffolded_code/`, and calls `create_bitbucket_branch_and_pr`).
4. **Deploy Both to Cloud Run & Authorize Service Accounts (`lab 3.pdf` Task 5)**:
   - Deploy with `agents-cli deploy`.
   - Grant each Cloud Run Service Account `roles/agentidentity.user` on `syf-mcp-auth-provider` and `roles/serviceusage.serviceUsageConsumer` on the project.
   - Verify A2A endpoints with `agents-cli run --url <URL> --mode a2a`.

#### Phase 4: Scaffold, Build & Deploy Agent Runtime Agents (`finops-agent` & `vpm-agent`)
1. **Scaffold via `agents-cli`**:
   ```bash
   agents-cli scaffold create finops-agent --agent adk --deployment-target agent_runtime --region $REGION --prototype --agent-guidance-filename GEMINI.md
   agents-cli scaffold create vpm-agent --agent adk --deployment-target agent_runtime --region $REGION --prototype --agent-guidance-filename GEMINI.md
   ```
2. **Build & Deploy `finops-agent` (Morgan) on Agent Runtime #1**:
   - Isolates `deep_research_analyst` (`tools=[google_search]`) and `finops_tco_analyst` (`McpToolset` with `GcpAuthProviderScheme`), orchestrated by Morgan's root agent.
   - Deploy to **Agent Runtime** with Agent Identity enabled (`deploy_with_identity.sh` / `--agent-identity`), extract its **SPIFFE principal** (`principal://agents.global.org-.../reasoningEngines/...`), and grant `roles/agentidentity.user` on `syf-mcp-auth-provider` (`lab 3.pdf` Task 3).
3. **Build & Deploy `vpm-agent` (Alex — Master Orchestrator) on Agent Runtime #2**:
   - **Antigravity Skills**: Bundles all 6 `SKILL.md` files + `list_antigravity_skills` & `activate_antigravity_skill` tools.
   - **A2A Specialists**: Connects to `finops-agent`, `arch-agent`, and `dev-agent` via `RemoteA2aAgent` / `AgentTool` (or direct A2A client tool).
   - **Cursor-Style Living Workspace**: Uses `McpToolset` (`save_workspace_document`, `patch_document_section`, `get_workspace_document`) to maintain `PRD-AI-EVAL-101.md`, `ADR-001-Eval-Gateway.md`, and `BACKLOG-AI-EVAL-101.json` in `gs://${PROJECT_ID}-syf-vpm-workspace/workspace_artifacts/`.
   - **HITL Approval Gate**: Enforces explicit human sign-off before executing `commit_approved_backlog_to_sdlc` (Jira Epic/Story creation, Confluence publish, and Devin code scaffolding).
   - **Vertex AI Memory Bank**: Uses `PreloadMemoryTool()` and `after_agent_callback=generate_memories_callback` (`await callback_context.add_session_to_memory()`) for long-term cross-session recall.
   - Deploy to **Agent Runtime** with Agent Identity enabled and grant its **SPIFFE principal** `roles/agentidentity.user` on `syf-mcp-auth-provider`, `roles/storage.objectAdmin` on the workspace bucket, and `roles/run.invoker` / `roles/aiplatform.user`.

#### Phase 5: Evaluation (`agents-cli eval`) & Registration with Gemini Enterprise (`agents-cli publish gemini`)
1. **Run Evaluation Suite (`agents-cli eval run`)**:
   - Evaluate `vpm-agent` against `multi_turn_task_success`, `multi_turn_trajectory_quality`, `multi_turn_tool_use_quality`, `safety`, and our custom `human_gate_compliance_judge` across the 4 benchmark scenarios (FinOps intake, Kong Curveball + Cursor inline diff, HITL gate, SDLC commit + code scaffold).
2. **Verify Cross-Session Vertex AI Memory Bank Recall**:
   - Run a two-session test verifying that decisions consolidated in Session 1 are automatically recalled by `PreloadMemoryTool()` in Session 2.
3. **Register Master Agent (`vpm-agent`) into Gemini Enterprise App (`google-agents-cli-publish`)**:
   ```bash
   # List available Gemini Enterprise apps in the project
   agents-cli publish gemini --list

   # Register vpm-agent (Alex) natively with Gemini Enterprise
   agents-cli publish gemini \
     --registration-type adk \
     --agent-runtime-id "$VPM_AGENT_RUNTIME_ID" \
     --gemini-app-id "$GEMINI_APP_ID" \
     --display-name "Alex - Synchrony Virtual Product Manager" \
     --description "Virtual PM orchestrating FinOps TCO research, Enterprise Architecture ADRs, Cursor-style living PRD/ADR edits, Jira/Bitbucket SDLC sync, and code scaffolding." \
     --tool-description "Consult Alex to draft/edit PRDs and ADRs, run FinOps vendor evaluations, assess architectural curveballs, create Jira backlogs, and scaffold OpenShift services."
   ```
4. **Generate Colleague Handoff Manifest**:
   - Export `A2A_HANDOFF_MANIFEST.md` with all 4 agents' A2A AgentCard URLs, Reasoning Engine IDs, SPIFFE principals, and Cloud Run URLs for your colleague's Gateway/Registry/Model Armor project.
