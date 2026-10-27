# Technical Design Document (TDD): Synchrony Financial (SYF) Virtual Product Manager Multi-Agent Platform

**Document Version:** 1.0  
**Target Customer:** Synchrony Financial (SYF) — Executive Sponsor: Dan Weis (VP of AI Innovation) & Nimrod Barak (CAIO)  
**Workspace Root:** `/home/admin_/vertexai-l300-capstone/virtual-product-manager`  
**Export Location:** `/home/admin_/SYF_VPM_Technical_Design_Document.md`

---

## 1. Executive Summary & Architectural Principles

This Technical Design Document (TDD) specifies the complete engineering blueprint for Synchrony Financial's **Virtual Product Manager (VPM)** multi-agent prototype. The platform combines:
1. **"Mimic Cursor" (Multi-File Context & Surgical Inline Editing)**: Living Markdown/JSON product artifacts (`PRD-AI-EVAL-101.md`, `ADR-001-Eval-Gateway.md`, `BACKLOG-AI-EVAL-101.json`) stored in a shared **Google Cloud Storage (GCS)** workspace bucket (`gs://${PROJECT_ID}-syf-vpm-workspace/`) that can be surgically patched section-by-section with unified line diffs (`-` / `+`).
2. **"Pull in Antigravity" (Progressive-Disclosure Domain Skills)**: 6 custom, Synchrony-specific `SKILL.md` packages built using the Antigravity Customization Specification (`name`/`description` YAML frontmatter + progressive disclosure `references/` and `resources/`) loaded on-demand by agents via tool calls.
3. **"Integrate with their SDLC" (End-to-End Loop & Blocker Sync)**: Human-in-the-Loop (HITL) gated creation of Jira Epics (`AI-EVAL-101`), Gherkin User Stories, SYF engineering squad assignments, Bitbucket feature branches/PRs, hardened OpenShift (ROSA) code scaffolding, and bidirectional Jira blocker impact synchronization.
4. **Hybrid Runtime & Zero-Trust Identity (Lab 3 `APEX013` Pattern)**:
   - **2 Agents on Vertex AI Agent Runtime** (`vpm-agent` & `finops-agent`) authenticating via **SPIFFE Principals** (`principal://agents.global.org-...`).
   - **2 Specialist Agents + 1 FastMCP Server on Cloud Run** (`arch-agent`, `dev-agent`, `syf-mcp-server`) authenticating via **Cloud Run Service Accounts**.
   - **Zero hardcoded secrets**: All tool credentials resolved dynamically at call-time through **Agent Identity Auth Manager** (`GcpAuthProvider` + `GcpAuthProviderScheme`).
5. **Gemini Enterprise (GE) Front-End + Colleague A2A Handoff**:
   - The master orchestrator (`vpm-agent`) is registered natively into your **Gemini Enterprise App** via `agents-cli publish gemini --registration-type adk`.
   - All 4 agents expose standards-compliant **A2A AgentCard URLs** (`/a2a/app/.well-known/agent-card.json`) for downstream registration with Agent Registry, Agent Gateway, and Model Armor in your colleague's governance project.

---

## 2. LLM & Thinking Mode Configuration Matrix (Strict Policy)

> **Strict Model Policy:** Only **`gemini-3.8-flash`** and **`gemini-3.5-flash-lite`** are permitted across the entire codebase. No legacy models (`gemini-1.5-*`, `gemini-2.0-*`, `gemini-2.5-*`) may be used anywhere. Both model ID and thinking level are parameterized via environment variables (`MODEL` and `THINKING_LEVEL`) so they can be swapped without code changes.

| Component / Agent | Persona & Role | Deployment Target | Default Model (`MODEL`) | Thinking Mode (`THINKING_LEVEL`) | Temperature | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`vpm-agent`** | **Alex** — Root Virtual PM Orchestrator | **Agent Runtime** | `gemini-3.8-flash` | `MEDIUM` | `0.1` | Handles complex multi-agent synthesis, trade-off reconciliation, Cursor-style surgical PRD diffs, HITL gating, and curveball orchestration. |
| **`finops-agent`** | **Morgan** — Deep Research & FinOps Analyst | **Agent Runtime** | `gemini-3.5-flash-lite` | `LOW` | `0.0` | Executes fast `google_search` grounding and deterministic MCP TCO benchmark lookups; low thinking minimizes multi-hop latency. |
| **`arch-agent`** | **Marcus** — Enterprise Architecture Specialist | **Cloud Run** | `gemini-3.5-flash-lite` | `LOW` | `0.0` | Evaluates structured compliance rules (`architecture_standards.json`) and deterministic curveball blast-radius calculations. |
| **`dev-agent`** | **Devin** — Developer & SDLC Scaffolder | **Cloud Run** | `gemini-3.5-flash-lite` | `LOW` | `0.0` | Generates deterministic OpenShift/ROSA boilerplate from golden skill templates and invokes Bitbucket branch/PR tools. |

### Standard ADK Model Initialization Snippet
```python
import os
from google.adk.models import Gemini
from google.genai import types

MODEL = os.environ.get("MODEL", "gemini-3.8-flash")          # or "gemini-3.5-flash-lite" for sub-agents
THINKING_LEVEL = os.environ.get("THINKING_LEVEL", "MEDIUM")  # or "LOW" for sub-agents

def build_model() -> Gemini:
    return Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    )

def build_generate_config(temperature: float = 0.1) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        temperature=temperature,
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
    )
```

---

## 3. Complete Folder Structure (Local Workspace & GCS Bucket)

### 3.1 Local Repository Layout (`/home/admin_/vertexai-l300-capstone/virtual-product-manager/`)

```text
/home/admin_/vertexai-l300-capstone/virtual-product-manager/
├── SYF_VPM_Technical_Design_Document.md     # This Technical Design Document
├── SYF_VPM_Blueprint.md                     # Executive Critique & Strategy Blueprint
├── A2A_HANDOFF_MANIFEST.md                  # Generated in Phase 5 for colleague's Gateway/Model Armor project
├── scripts/
│   ├── setup_gcp_and_auth_manager.sh        # Phase 1: APIs, GCS bucket creation/sync, Auth Manager provider
│   ├── deploy_with_identity.sh              # Lab 3 two-step Agent Runtime + SPIFFE identity deployment script
│   └── verify_e2e_and_memory.py             # Phase 5: E2E scenario + Memory Bank latency/recall verification
│
├── shared_skills/                           # Master copy of the 6 Synchrony Domain Skills (synced to GCS & agents)
│   ├── syf-prd-authoring/
│   │   ├── SKILL.md
│   │   └── resources/prd_template.md
│   ├── syf-finops-tco-modeling/
│   │   ├── SKILL.md
│   │   └── references/tco_formulas.md
│   ├── syf-zero-trust-compliance/
│   │   ├── SKILL.md
│   │   └── references/pci_hipaa_entraid_rules.md
│   ├── syf-sdlc-backlog-sync/
│   │   ├── SKILL.md
│   │   └── resources/gherkin_story_schema.json
│   ├── syf-rosa-gateway-scaffolding/
│   │   ├── SKILL.md
│   │   └── resources/golden_templates.md
│   └── syf-executive-curveball-playbook/
│       ├── SKILL.md
│       └── references/curveball_decision_matrix.md
│
├── syf-mcp-server/                          # Service 1 (Cloud Run): Synchrony Enterprise FastMCP Server
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── server.py                            # FastMCP Streamable HTTP (/mcp on port 8080) backed by GCS
│   ├── gcs_store.py                         # Read/write helper for gs://${PROJECT_ID}-syf-vpm-workspace/
│   └── seed_data/
│       ├── eval_vendor_benchmarks.json      # Arize, Braintrust, Langfuse unit economics & scaling tiers
│       ├── architecture_standards.json      # PCI-DSS, CareCredit HIPAA, Entra ID, Kong deprecation, ROSA/Cloud Run
│       └── jira_seed_templates.json         # Jira project keys, SYF squads, Gherkin templates, Bitbucket repos
│
├── arch-agent/                              # Agent 1 (Cloud Run): Marcus — Enterprise Architecture Specialist
│   ├── agents-cli-manifest.yaml             # Generated by `agents-cli scaffold create`
│   ├── Dockerfile
│   ├── pyproject.toml                       # google-adk[gcp,agent-identity,mcp]
│   ├── GEMINI.md
│   └── app/
│       ├── __init__.py
│       ├── agent.py                         # root_agent (gemini-3.5-flash-lite, thinking=LOW)
│       ├── tools.py                         # McpToolset (GcpAuthProviderScheme) + evaluate_curveball_impact
│       ├── skills/                          # Bundled syf-zero-trust-compliance & syf-executive-curveball-playbook
│       ├── fast_api_app.py                  # A2A (/a2a/app/.well-known/agent-card.json) + OTEL
│       └── app_utils/
│
├── dev-agent/                               # Agent 2 (Cloud Run): Devin — Developer & SDLC Scaffolder
│   ├── agents-cli-manifest.yaml             # Generated by `agents-cli scaffold create`
│   ├── Dockerfile
│   ├── pyproject.toml                       # google-adk[gcp,agent-identity,mcp]
│   ├── GEMINI.md
│   └── app/
│       ├── __init__.py
│       ├── agent.py                         # root_agent (gemini-3.5-flash-lite, thinking=LOW)
│       ├── tools.py                         # scaffold_evaluation_gateway + McpToolset (Bitbucket PRs & GCS write)
│       ├── skills/                          # Bundled syf-rosa-gateway-scaffolding & syf-sdlc-backlog-sync
│       ├── fast_api_app.py                  # A2A (/a2a/app/.well-known/agent-card.json) + OTEL
│       └── app_utils/
│
├── finops-agent/                            # Agent 3 (Agent Runtime #1): Morgan — Deep Research & FinOps Analyst
│   ├── agents-cli-manifest.yaml             # Generated by `agents-cli scaffold create`
│   ├── deployment_metadata.json
│   ├── Dockerfile
│   ├── pyproject.toml                       # google-adk[gcp,agent-identity,mcp]
│   ├── GEMINI.md
│   └── app/
│       ├── __init__.py
│       ├── agent.py                         # root_agent (gemini-3.5-flash-lite, thinking=LOW) + google_search sub-agent
│       ├── tools.py                         # McpToolset with SPIFFE GcpAuthProviderScheme -> syf-mcp-server
│       ├── skills/                          # Bundled syf-finops-tco-modeling
│       ├── fast_api_app.py                  # Reasoning Engine Adapter + A2A routes
│       └── app_utils/
│
└── vpm-agent/                               # Agent 4 (Agent Runtime #2): Alex — Master VPM Orchestrator
    ├── agents-cli-manifest.yaml             # Generated by `agents-cli scaffold create`
    ├── deployment_metadata.json
    ├── Dockerfile
    ├── pyproject.toml                       # google-adk[gcp,agent-identity,mcp]
    ├── GEMINI.md
    ├── app/
    │   ├── __init__.py
    │   ├── agent.py                         # root_agent (gemini-3.8-flash, thinking=MEDIUM)
    │   ├── tools.py                         # A2A specialist callers, Cursor inline diff tools, HITL gate, Skill loader
    │   ├── memory_manager.py                # Latency-optimized Vertex AI Memory Bank callbacks & LoadMemoryTool
    │   ├── skills/                          # All 6 Synchrony Domain Skills bundled
    │   ├── fast_api_app.py                  # Reasoning Engine Adapter (:streamQuery for GE App) + A2A routes
    │   └── app_utils/
    └── tests/
        └── eval/
            ├── eval_config.yaml             # Canonical agents-cli eval configuration
            └── datasets/
                └── vpm_eval_dataset.json    # Multi-scenario evaluation dataset
```

### 3.2 Google Cloud Storage (GCS) Bucket Layout (`gs://${PROJECT_ID}-syf-vpm-workspace/`)

```text
gs://${PROJECT_ID}-syf-vpm-workspace/
├── seed_data/
│   ├── eval_vendor_benchmarks.json          # FinOps vendor pricing, span tiers, ROSA infra costs
│   ├── architecture_standards.json          # Synchrony enterprise security, network & runtime policies
│   └── jira_seed_templates.json             # Jira project metadata, SYF squads, Bitbucket repo targets
├── skills/                                  # Cloud mirror of all 6 Synchrony SKILL.md packages
│   ├── syf-prd-authoring/SKILL.md
│   ├── syf-finops-tco-modeling/SKILL.md
│   ├── syf-zero-trust-compliance/SKILL.md
│   ├── syf-sdlc-backlog-sync/SKILL.md
│   ├── syf-rosa-gateway-scaffolding/SKILL.md
│   └── syf-executive-curveball-playbook/SKILL.md
├── workspace_artifacts/                     # "Cursor-Style" Living Product Files (mutated in real time)
│   ├── PRD-AI-EVAL-101.md                   # Current latest PRD markdown
│   ├── ADR-001-Eval-Gateway.md              # Current latest Architecture Decision Record
│   ├── BACKLOG-AI-EVAL-101.json             # Live Jira Epic, Stories, Blockers, & Bitbucket PR state
│   └── history/                             # Version snapshots (e.g., PRD-AI-EVAL-101.v1.md, .v2.md)
└── scaffolded_code/                         # Generated by dev-agent (Devin) after HITL approval
    ├── Dockerfile
    ├── proxy_gateway.py
    ├── k8s_deployment.yaml
    └── requirements.txt
```

---

## 4. Specification of the 6 Synchrony Domain Skills (`shared_skills/`)

Built using the **Antigravity Customization System** (`agy-customizations`: YAML frontmatter with `name` and third-person `description` + progressive disclosure via `references/` and `resources/`). These are **purpose-built for Synchrony Financial's domain** (not copies of `agents-cli` skills).

### How Agents Discover & Load Skills at Runtime
- **Progressive Disclosure**: Base system instructions only list the 6 skill names and 1-line descriptions (`~180 tokens total`).
- **On-Demand Tool Activation**:
  - `list_syf_skills() -> dict`: Lists available Synchrony skills and their frontmatter descriptions.
  - `load_syf_skill(skill_name: str, include_references: bool = False) -> dict`: Reads `SKILL.md` (and optional `references/` / `resources/`) from the local `app/skills/` directory (or GCS fallback) and returns the specialized runbook into the current turn context.

### The 6 Synchrony Skills

#### Skill 1: `syf-prd-authoring`
```yaml
---
name: syf-prd-authoring
description: >-
  Use this skill when drafting a new Synchrony Financial Product Requirements Document (PRD)
  or performing Cursor-style surgical inline edits on specific sections of an existing PRD.
---
```
- **Core Procedure**:
  1. Enforces Synchrony's mandatory 5-section PRD schema (`## 1. Executive Summary & Strategic Imperative`, `## 2. FinOps TCO & Unit Economics`, `## 3. Target Multi-Cloud Architecture`, `## 4. Security, Ingress & Compliance Boundaries`, `## 5. Phased Rollout, Sprint Velocity & KPIs`).
  2. Defines rules for **Cursor-Style Surgical Inline Editing**: never overwrite the entire file when a stakeholder requests a section change or throws a curveball; invoke `patch_document_section(document_name="PRD-AI-EVAL-101.md", section_header=..., new_section_markdown=..., edit_reason=...)` and display the unified line diff (`-` / `+`) to the user.
- **Bundled Resource**: `resources/prd_template.md`.

#### Skill 2: `syf-finops-tco-modeling`
```yaml
---
name: syf-finops-tco-modeling
description: >-
  Use this skill when calculating Total Cost of Ownership (TCO), unit economics per million
  telemetry spans, or comparing AI evaluation vendors (Arize AX, Braintrust, Langfuse).
---
```
- **Core Procedure**:
  1. Instructs Morgan (`finops-agent`) and Alex (`vpm-agent`) to always pair live web grounding (`google_search` for latest OTel support, CVEs, and enterprise licensing changes) with internal financial telemetry (`query_vendor_cost_benchmarks`).
  2. Defines Synchrony's TCO formula:
     $$\text{Annual TCO} = \text{Base License} + \left(\text{Monthly Spans in Millions} \times 12 \times \text{Cost per 1M Spans}\right) + \text{Annual ROSA/ClickHouse Compute} + \text{Cross-Cloud Egress Penalty}$$
  3. Provides sensitivity analysis rules for 5M spans/mo (baseline) vs. 50M spans/mo (9,000 GECX contact center expansion).
- **Bundled Reference**: `references/tco_formulas.md`.

#### Skill 3: `syf-zero-trust-compliance`
```yaml
---
name: syf-zero-trust-compliance
description: >-
  Use this skill when evaluating system architectures against Synchrony Financial's CISO and CTO
  standards, including PCI-DSS v4.0, CareCredit HIPAA PHI rules, Microsoft Entra ID mTLS/JWKS,
  and API gateway / service mesh topology, or when authoring an Architecture Decision Record (ADR).
---
```
- **Core Procedure**:
  1. **Data Residency & Zero-Egress Rule**: Any system handling Tier-1 Cardholder Data (`PAN`, `CVV`, `SSN`) or CareCredit Protected Health Information (`PHI`, `ICD-10`, `MRN`) is strictly prohibited from multi-tenant third-party SaaS egress (`REJECTED: Non-Compliant`). Must deploy self-hosted in Synchrony VPC (AWS ROSA OpenShift or Google Cloud Run Private Subnets).
  2. **Identity & Ingress Standard**: Requires Microsoft Entra ID OAuth 2.0 / OIDC JWT validation with local JWKS caching (`5-min TTL` to meet `<25ms` P95 proxy overhead) and strict mTLS (`TLS 1.3`).
  3. **Gateway Deprecation Mandate**: Flags Kong Enterprise Gateway v3.4 as deprecated effective Q1; requires Envoy-based Internal Service Mesh (`mesh.syf.bank/injected: "true"`) or Apigee Hybrid ingress.
- **Bundled Reference**: `references/pci_hipaa_entraid_rules.md`.

#### Skill 4: `syf-sdlc-backlog-sync`
```yaml
---
name: syf-sdlc-backlog-sync
description: >-
  Use this skill when translating approved PRD and ADR requirements into Jira Epics, Gherkin
  User Stories, Fibonacci story points, SYF squad assignments, Bitbucket feature branches,
  or synchronizing engineering ticket blockers back into the PRD.
---
```
- **Core Procedure**:
  1. Enforces **Human-in-the-Loop (HITL) Gate**: Never call `create_jira_epic`, `create_jira_story`, `publish_confluence_prd`, or `create_bitbucket_branch_and_pr` until the human executive explicitly replies with approval.
  2. Formats every Jira story with strict **Gherkin Acceptance Criteria** (`Given / When / Then`), Fibonacci story points (`1, 2, 3, 5, 8, 13`), assigned Synchrony engineering squad (`SYF-Platform-Mesh-Squad`, `SYF-AI-FinOps-Squad`, `SYF-SecOps-DLP-Squad`), and linked Bitbucket repository branch (`feature/AI-EVAL-101-...`).
  3. Defines the **Continuous Lifecycle Blocker Sync** workflow (`sync_sdlc_ticket_blocker`): when a developer logs a blocker on a Jira story, calculate sprint delay, update the story's acceptance criteria, and surgically patch the affected PRD/ADR section.
- **Bundled Resource**: `resources/gherkin_story_schema.json`.

#### Skill 5: `syf-rosa-gateway-scaffolding`
```yaml
---
name: syf-rosa-gateway-scaffolding
description: >-
  Use this skill when generating production-ready container images, FastAPI OpenTelemetry
  collector proxies, inline PII/PCI/HIPAA redaction middleware, and OpenShift (ROSA) or
  Cloud Run deployment manifests.
---
```
- **Core Procedure**:
  1. **Base Image Standard**: `registry.access.redhat.com/ubi9/python-312:latest` running as non-root UID `1001`.
  2. **Safe Inline Redaction Rule (Zero `eval()`)**: Never use `eval()` on request payloads. Serialize payload via `json.dumps()`, apply compiled regex scrubbers for `PAN` (`[REDACTED_PAN]`), `SSN` (`[REDACTED_SSN]`), and `HIPAA_MRN` (`[REDACTED_MRN]`), and deserialize via `json.loads()`.
  3. **OpenTelemetry W3C TraceContext**: Extract or inject `traceparent` headers and forward sanitized spans asynchronously (`httpx.AsyncClient`) to the internal Langfuse ClickHouse collector within the `<25ms` P95 latency budget.
- **Bundled Resource**: `resources/golden_templates.md`.

#### Skill 6: `syf-executive-curveball-playbook`
```yaml
---
name: syf-executive-curveball-playbook
description: >-
  Use this skill when an executive or stakeholder introduces a mid-session scope change,
  architectural deprecation, volume surge, compliance mandate, or infrastructure constraint
  ("Wicked Curveball") that requires blast-radius recalculation across timeline, budget, and specs.
---
```
- **Core Procedure**:
  1. Immediately invoke `evaluate_curveball_impact` (via `arch-agent`) and `query_vendor_cost_benchmarks` (via `finops-agent` if volume changed).
  2. Surgically patch both `PRD-AI-EVAL-101.md` and `ADR-001-Eval-Gateway.md` in GCS using `patch_document_section` so the workspace artifacts reflect the pivot with a visible before/after diff.
  3. Present the updated sprint delta, TCO delta, and modified Jira story breakdown, then **halt at the HITL approval gate** for executive sign-off.
- **Bundled Reference**: `references/curveball_decision_matrix.md`.

---

## 5. Complete Specification of All Artifacts & Data Schemas

### 5.1 Seed Data Files (`syf-mcp-server/seed_data/` & `gs://${PROJECT_ID}-syf-vpm-workspace/seed_data/`)

#### A. `eval_vendor_benchmarks.json`
Contains structured pricing, compliance posture, and dynamic scaling parameters for:
- **Arize AX Enterprise (SaaS)**:
  - `base_annual_license_usd`: `85000`
  - `cost_per_million_spans_usd`: `1666.67` (yields `$100,000/yr` at 5M spans/mo -> **`$185,000/yr` total TCO**; yields `$1,000,000/yr` span cost at 50M spans/mo -> **`$1,085,000/yr` total TCO**)
  - `deployment_model`: `"SaaS (Multi-Tenant Cloud)"`
  - `pci_dss_zero_egress_compliant`: `false`
- **Braintrust Enterprise (Hybrid)**:
  - `base_annual_license_usd`: `60000`
  - `cost_per_million_spans_usd`: `1250.00` (yields `$75,000/yr` at 5M spans/mo -> **`$135,000/yr` total TCO**)
  - `deployment_model`: `"Hybrid (Control Plane in Vendor Cloud, Data Plane Proxy)"`
  - `pci_dss_zero_egress_compliant`: `false` (metadata egresses to vendor control plane)
- **Langfuse Enterprise (Self-Hosted on ROSA / Cloud Run)**:
  - `base_annual_license_usd`: `36000`
  - `cost_per_million_spans_usd`: `0.0` (unlimited self-hosted spans)
  - `rosa_compute_base_annual_usd`: `40000` (at 5M spans/mo -> **`$76,000/yr` total TCO**, saving **`$109,000/yr`** vs. Arize!)
  - `rosa_compute_per_additional_10m_spans_usd`: `12000` (at 50M spans/mo -> `$36k license + $94k ClickHouse cluster = $130,000/yr`, saving **`$955,000/yr`** vs. Arize!)
  - `deployment_model`: `"Self-Hosted Container (ROSA OpenShift / GCP Cloud Run Private VPC)"`
  - `pci_dss_zero_egress_compliant`: `true`

#### B. `architecture_standards.json`
Contains Synchrony's authoritative enterprise architecture policies and the 5 Curveball rules:
- `security_and_compliance`: PCI-DSS v4.0 Tier-1 zero-egress mandate, CareCredit HIPAA PHI redaction mandate, Model Armor / regex inline scrubbing (`SSN`, `PAN`, `MRN`, `ICD10`).
- `identity_and_access`: Microsoft Entra ID OAuth 2.0 / OIDC JWT + JWKS local caching (`300s TTL`), mTLS (`TLS 1.3`).
- `api_gateway_and_mesh`:
  - `current_gateway`: `"Kong Enterprise Gateway v3.4"`
  - `deprecation_notice`: `"CRITICAL: Kong Enterprise Gateway is deprecated effective Q1. All new Tier-1 services must use Synchrony Internal Service Mesh (Envoy sidecar injection: mesh.syf.bank/injected=true) or Apigee Hybrid."`
- `approved_runtimes`: `["AWS Red Hat OpenShift (ROSA)", "Google Cloud Run Private Subnets (PSC)"]`
- `curveball_catalog`: Deterministic blast-radius definitions for `CB-1` (Kong deprecation: `+2 sprints`, `+$32,000`), `CB-2` (50M GECX span surge: `+1 sprint` ClickHouse sharding, `$955k/yr` TCO savings), `CB-3` (CareCredit HIPAA PHI mandate: `+1 sprint` DLP sidecar), `CB-4` (ROSA freeze -> Cloud Run Private Subnets pivot: `-1 sprint` accelerated delivery), and `CB-5` (Entra ID JWKS caching blocker fix: `+0 sprints`, `<2ms` auth latency).

#### C. `jira_seed_templates.json`
Contains Synchrony Jira project configuration (`project_key: "AIEVAL"`, `board_name: "SYF AI Platform Engineering"`), engineering squad rosters (`SYF-Platform-Mesh-Squad`, `SYF-AI-FinOps-Squad`, `SYF-SecOps-DLP-Squad`), Bitbucket repository URLs (`https://bitbucket.syf.bank/scm/aiplat/langfuse-eval-gateway.git`), and active developer blockers (e.g., `AI-STORY-102` Entra ID token introspection latency blocker).

---

### 5.2 Living "Cursor-Style" Workspace Artifacts (`gs://${PROJECT_ID}-syf-vpm-workspace/workspace_artifacts/`)

1. **`PRD-AI-EVAL-101.md`**:
   - Multi-section Markdown document with deterministic `## N. Section Name` headers.
   - Tracks version metadata in YAML header (`version: 1.0`, `last_modified_by`, `status: DRAFT | CURVEBALL_UPDATED | APPROVED`).
   - Supports surgical section replacement via `patch_document_section`, returning a unified diff (`difflib.unified_diff`) so the user sees exact `-` / `+` line edits in Gemini Enterprise.
2. **`ADR-001-Eval-Gateway.md`**:
   - Architecture Decision Record capturing Context, FinOps vs. Security Trade-Off Debate (Morgan vs. Marcus), Consensus Decision, Ingress/Mesh Topology, and Consequences.
3. **`BACKLOG-AI-EVAL-101.json`**:
   - JSON state file tracking the Epic (`AI-EVAL-101`), all generated Gherkin User Stories (`AI-STORY-101` .. `AI-STORY-105`), story points, sprint numbers, squad assignees, Bitbucket branch/PR links, and approval status (`PENDING_APPROVAL` vs. `COMMITTED`).

---

### 5.3 Devin's Scaffolded Code Artifacts (`gs://${PROJECT_ID}-syf-vpm-workspace/scaffolded_code/`)

Generated dynamically by `dev-agent` (Devin) once Dan Weis approves the backlog:
1. **`Dockerfile`**: Hardened Red Hat UBI9 (`registry.access.redhat.com/ubi9/python-312:latest`), non-root user `1001`, FIPS-compliant flags, uvicorn worker startup on port `8080`.
2. **`proxy_gateway.py`**: Production-grade FastAPI microservice implementing:
   - W3C `traceparent` OpenTelemetry header validation/generation.
   - Safe JSON serialization + regex PII/PCI/HIPAA scrubbing (`sanitize_telemetry_payload` using `json.dumps` -> `PAN_REGEX` / `SSN_REGEX` / `MRN_REGEX` -> `json.loads`, **zero `eval()`**).
   - Entra ID JWT bearer verification stub with local JWKS cache.
   - Async forwarding (`httpx.AsyncClient`) to internal Langfuse collector.
3. **`k8s_deployment.yaml`**: OpenShift/ROSA `Deployment` and `Service` manifest with `mesh.syf.bank/injected: "true"`, `security.syf.bank/pci-tier: "tier-1-redacted"`, resource requests/limits, and `/healthz` probes.
4. **`requirements.txt`**: Pinned dependencies (`fastapi`, `uvicorn`, `httpx`, `pydantic`, `opentelemetry-api`, `opentelemetry-sdk`).

---

## 6. Agent-by-Agent Technical Architecture & Lab 3 Auth Manager Wiring

### 6.1 Agent Identity Auth Manager Design (Lab 3 `APEX013` Pattern)

Following `lab 3.pdf`, **no agent stores an API key or secret in its code or `.env`**. Instead:
1. We create an API-Key Auth Provider in **Agent Identity Auth Manager**:
   ```bash
   gcloud alpha agent-identity auth-providers create syf-mcp-auth-provider \
     --project=${PROJECT_ID} \
     --location=${LOCATION} \
     --api-key="${SYF_MCP_API_KEY}"
   ```
2. Every agent registers `CredentialManager.register_auth_provider(GcpAuthProvider())` at import time and passes `GcpAuthProviderScheme(name=SYF_MCP_AUTH_PROVIDER_URI)` + `header_provider=syf_mcp_header_provider` to its `McpToolset`:
   ```python
   from google.adk.auth.credential_manager import CredentialManager
   from google.adk.integrations.agent_identity import GcpAuthProvider, GcpAuthProviderScheme
   from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

   CredentialManager.register_auth_provider(GcpAuthProvider())
   syf_auth_scheme = GcpAuthProviderScheme(name=SYF_MCP_AUTH_PROVIDER_URI)

   def build_syf_mcp_toolset(tool_filter: list[str]) -> McpToolset:
       toolset = None
       def syf_header_provider(readonly_ctx) -> dict[str, str]:
           if not toolset or not toolset.get_auth_config():
               return {}
           auth_config = toolset.get_auth_config()
           cred = None
           if readonly_ctx and hasattr(readonly_ctx, "get_credential"):
               cred = readonly_ctx.get_credential(auth_config.credential_key)
           if not cred:
               cred = auth_config.exchanged_auth_credential
           if not cred or not cred.http:
               return {}
           token = None
           if cred.http.credentials and cred.http.credentials.token:
               token = cred.http.credentials.token
           elif cred.http.additional_headers:
               token = (
                   cred.http.additional_headers.get("X-API-Key")
                   or cred.http.additional_headers.get("X-GOOG-API-KEY")
               )
           if token:
               return {"Authorization": f"Bearer {token}"}
           return {}

       toolset = McpToolset(
           connection_params=StreamableHTTPConnectionParams(url=SYF_MCP_URL),
           auth_scheme=syf_auth_scheme,
           tool_filter=tool_filter,
           header_provider=syf_header_provider,
       )
       return toolset
   ```
3. **Two Runtimes, Two Identities**:
   - **Agent Runtime Agents (`vpm-agent`, `finops-agent`)**: Granted `roles/agentidentity.user` on `syf-mcp-auth-provider` via their **SPIFFE principal** (`principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${ENGINE_ID}`).
   - **Cloud Run Agents (`arch-agent`, `dev-agent`)**: Granted `roles/agentidentity.user` on `syf-mcp-auth-provider` via their **Cloud Run Service Account** (`serviceAccount:${SA_EMAIL}`).

---

### 6.2 Latency-Optimized Vertex AI Memory Bank Architecture (`vpm-agent/app/memory_manager.py`)

> **Why We Optimize `PreloadMemoryTool()`**:
> In ADK, `PreloadMemoryTool()` hooks into `process_llm_request`, which executes before **every single LLM call** inside a turn. In a multi-agent orchestrator that calls 3–4 tools/sub-agents in a single user turn, `PreloadMemoryTool()` makes 4–5 redundant network round-trips to Vertex AI Memory Bank per turn, adding significant tail latency.

**Our 3-Part Optimization Strategy**:
1. **Sub-Agents Never Call Memory Bank**: `finops-agent`, `arch-agent`, and `dev-agent` have zero memory tools attached.
2. **Session-Cached Turn-1 Preload + On-Demand `LoadMemoryTool` on Root Agent (`vpm-agent`)**:
   - We attach `LoadMemoryTool()` (`from google.adk.tools.load_memory_tool import LoadMemoryTool`) instead of `PreloadMemoryTool()`, OR use a lightweight `before_agent_callback` that checks `callback_context.state.get("memory_loaded_for_session")`:
     - On **Turn 1** of a new session, `before_agent_callback` queries `callback_context._invocation_context.memory_service.search_memory(...)` **once** (with a strict `2.5s` timeout), caches the summary in `callback_context.state["executive_memory_context"]`, and sets `state["memory_loaded_for_session"] = True`.
     - On **Turns 2..N** (and during all intra-turn tool/sub-agent loops), zero automatic Memory Bank RPCs are fired—eliminating per-step latency! If Alex explicitly needs to search older memories mid-conversation, it calls `LoadMemoryTool()` on demand.
   - Controlled via env var `MEMORY_STRATEGY=session_cached` (options: `session_cached` [default], `on_demand`, `preload`, `disabled`) so we can tune latency effortlessly during testing.
3. **Non-Blocking Memory Consolidation (`after_agent_callback`)**:
   - `generate_memories_callback` calls `await callback_context.add_session_to_memory()` at the completion of the root agent's turn (and persists a human-readable snapshot to `gs://${PROJECT_ID}-syf-vpm-workspace/workspace_artifacts/MEMORY_BANK_LOG.json` for demo visibility).

---

## 7. Step-by-Step Implementation Plan

### Phase 1: Environment, GCS Bucket & Agent Identity Auth Manager Setup
1. **Run `scripts/setup_gcp_and_auth_manager.sh`**:
   - Enables required GCP APIs (`aiplatform`, `run`, `cloudbuild`, `storage`, `discoveryengine`, `agentidentity`, `agentidentitycredentials`, `iamcredentials`, `sts`).
   - Creates `gs://${PROJECT_ID}-syf-vpm-workspace` and uploads `seed_data/` (`eval_vendor_benchmarks.json`, `architecture_standards.json`, `jira_seed_templates.json`) and `shared_skills/` (all 6 `SKILL.md` directories).
   - Creates `syf-mcp-auth-provider` in Agent Identity Auth Manager (`gcloud alpha agent-identity auth-providers create`) and grants `roles/agentidentity.user` to the active developer account for local testing.

### Phase 2: Build & Deploy `syf-mcp-server` on Cloud Run
1. **Create `syf-mcp-server/`**:
   - Implement `gcs_store.py` (reads/writes JSON and Markdown files in `gs://${PROJECT_ID}-syf-vpm-workspace/` with local disk fallback).
   - Implement `server.py` (FastMCP Streamable HTTP on `/mcp`, port `8080`) with Bearer API-key verification and 11 tools:
     - `query_vendor_cost_benchmarks`
     - `get_architecture_standards`
     - `list_workspace_documents`
     - `get_workspace_document`
     - `save_workspace_document`
     - `patch_document_section` (Cursor-style surgical section replacement + unified diff)
     - `create_jira_epic`
     - `create_jira_story`
     - `publish_confluence_prd`
     - `create_bitbucket_branch_and_pr`
     - `sync_sdlc_ticket_blocker`
2. **Deploy `syf-mcp-server` to Cloud Run** and verify `/mcp` tool listing and execution.

### Phase 3: Scaffold, Build & Deploy Cloud Run Specialist Agents (`arch-agent` & `dev-agent`)
1. **Scaffold both projects via `agents-cli`**:
   ```bash
   agents-cli scaffold create arch-agent --agent adk --deployment-target cloud_run --region $REGION --prototype --agent-guidance-filename GEMINI.md
   agents-cli scaffold create dev-agent --agent adk --deployment-target cloud_run --region $REGION --prototype --agent-guidance-filename GEMINI.md
   ```
2. **Implement `arch-agent` (Marcus — `gemini-3.5-flash-lite`, `thinking_level=LOW`)**:
   - Bundle `syf-zero-trust-compliance` and `syf-executive-curveball-playbook` skills.
   - Wire `McpToolset` with `GcpAuthProviderScheme` (`get_architecture_standards`, `get_workspace_document`, `patch_document_section`) + `evaluate_curveball_impact` tool covering all 5 Curveballs (`CB-1` to `CB-5`).
3. **Implement `dev-agent` (Devin — `gemini-3.5-flash-lite`, `thinking_level=LOW`)**:
   - Bundle `syf-rosa-gateway-scaffolding` and `syf-sdlc-backlog-sync` skills.
   - Wire `McpToolset` with `GcpAuthProviderScheme` + `scaffold_evaluation_gateway` tool (generates `Dockerfile`, safe RCE-free `proxy_gateway.py`, `k8s_deployment.yaml`, `requirements.txt` into `gs://${PROJECT_ID}-syf-vpm-workspace/scaffolded_code/` and creates the Bitbucket branch/PR).
4. **Local Smoke Test & Cloud Run Deployment**:
   - Test both locally with `agents-cli run`.
   - Deploy both to Cloud Run via `agents-cli deploy`.
   - Grant both Cloud Run Service Accounts `roles/agentidentity.user` on `syf-mcp-auth-provider`, `roles/serviceusage.serviceUsageConsumer`, and `roles/storage.objectAdmin` on the workspace bucket.
   - Verify both A2A endpoints with `agents-cli run --url <CLOUD_RUN_URL> --mode a2a`.

### Phase 4: Scaffold, Build & Deploy Agent Runtime Agents (`finops-agent` & `vpm-agent`)
1. **Scaffold both projects via `agents-cli`**:
   ```bash
   agents-cli scaffold create finops-agent --agent adk --deployment-target agent_runtime --region $REGION --prototype --agent-guidance-filename GEMINI.md
   agents-cli scaffold create vpm-agent --agent adk --deployment-target agent_runtime --region $REGION --prototype --agent-guidance-filename GEMINI.md
   ```
2. **Implement & Deploy `finops-agent` (Morgan — `gemini-3.5-flash-lite`, `thinking_level=LOW`) on Agent Runtime #1**:
   - Bundle `syf-finops-tco-modeling` skill.
   - Isolate `deep_research_subagent` (`tools=[google_search]`) from `finops_mcp_toolset` (`query_vendor_cost_benchmarks` via `GcpAuthProviderScheme`) using `AgentTool`.
   - Deploy to Agent Runtime with Agent Identity enabled (`scripts/deploy_with_identity.sh`), bind its **SPIFFE principal** to `syf-mcp-auth-provider` (`roles/agentidentity.user`), and verify via `agents-cli run --url <ENGINE_URL> --mode a2a`.
3. **Implement & Deploy `vpm-agent` (Alex — `gemini-3.8-flash`, `thinking_level=MEDIUM`) on Agent Runtime #2**:
   - Bundle all 6 Synchrony `SKILL.md` skills + `list_syf_skills` and `load_syf_skill` tools.
   - Wire A2A specialist delegation tools (`consult_morgan_finops`, `consult_marcus_architecture`, `delegate_to_devin_scaffolder`) invoking the deployed `finops-agent`, `arch-agent`, and `dev-agent` endpoints.
   - Wire Cursor-style workspace tools (`save_workspace_document`, `patch_document_section`, `get_workspace_document`) and HITL-gated SDLC execution tools (`commit_approved_backlog_to_jira_and_confluence`, `sync_sdlc_ticket_blocker`) via `McpToolset` (`GcpAuthProviderScheme`).
   - Wire latency-optimized Vertex AI Memory Bank (`memory_manager.py` with `MEMORY_STRATEGY=session_cached` + `LoadMemoryTool()` + `after_agent_callback`).
   - Deploy to Agent Runtime with Agent Identity enabled, bind its **SPIFFE principal** to `syf-mcp-auth-provider` (`roles/agentidentity.user`), and grant `roles/run.invoker` + `roles/aiplatform.user` + `roles/storage.objectAdmin`.

### Phase 5: Evaluation (`agents-cli eval`), Memory Verification & Gemini Enterprise Registration (`agents-cli publish gemini`)
1. **Run `agents-cli eval run` on `vpm-agent`**:
   - Execute evaluation dataset (`tests/eval/datasets/vpm_eval_dataset.json`) against `multi_turn_task_success`, `multi_turn_trajectory_quality`, `multi_turn_tool_use_quality`, `safety`, and custom `human_gate_compliance_judge`.
2. **Run Cross-Session Memory Bank & Latency Verification (`scripts/verify_e2e_and_memory.py`)**:
   - Verify end-to-end latency and confirm that architectural pivots consolidated in Session 1 are recalled in Session 2.
3. **Register `vpm-agent` with Gemini Enterprise App**:
   ```bash
   agents-cli publish gemini --list
   agents-cli publish gemini \
     --registration-type adk \
     --agent-runtime-id "$VPM_AGENT_RUNTIME_ID" \
     --gemini-app-id "$GEMINI_APP_ID" \
     --display-name "Alex - Synchrony Virtual Product Manager" \
     --description "Virtual PM orchestrating FinOps TCO research, Enterprise Architecture ADRs, Cursor-style living PRD/ADR edits, Jira/Bitbucket SDLC sync, and code scaffolding." \
     --tool-description "Consult Alex to draft/edit PRDs and ADRs, run FinOps vendor evaluations, assess architectural curveballs, create Jira backlogs, and scaffold OpenShift services."
   ```
4. **Export `A2A_HANDOFF_MANIFEST.md`**:
   - Document all deployed A2A AgentCard URLs, Reasoning Engine IDs, SPIFFE principals, and Cloud Run Service URLs for your colleague's Gateway/Registry/Model Armor project.
