# Synchrony Financial (SYF) Virtual Product Manager — A2A & Governance Handoff Manifest

> **Purpose**: This manifest provides all live endpoints, A2A Agent Card URLs, Vertex AI Agent Runtime resource URIs, SPIFFE Principal Identities, Cloud Run Service Account Identities, and Agent Identity Auth Manager configurations deployed in **`vertexai-l300-capstone` (`121190797389`)**. Use this manifest to register the agents in **Google Cloud Agent Registry**, bind them to **Agent Gateway**, and attach **Model Armor** floorplates in the governance project.

---

## 1. Environment & Project Metadata

| Parameter | Value |
| :--- | :--- |
| **GCP Project ID** | `vertexai-l300-capstone` |
| **GCP Project Number** | `121190797389` |
| **GCP Organization ID** | `526625392936` |
| **Primary Region** | `us-central1` |
| **Gemini 3.x Model Endpoint Location** | `global` (`gemini-3.8-flash` & `gemini-3.5-flash-lite`) |
| **Living Product Workspace Bucket** | `gs://vertexai-l300-capstone-syf-vpm-workspace` |
| **Agent Identity Auth Provider URI** | `projects/vertexai-l300-capstone/locations/us-central1/authProviders/syf-mcp-auth-provider` |
| **Gemini Enterprise App ID** | `projects/121190797389/locations/global/collections/default_collection/engines/gemini-enterprise-17606215_1760621535927` |
| **Registered Gemini Enterprise Agent Name** | `projects/121190797389/locations/global/collections/default_collection/engines/gemini-enterprise-17606215_1760621535927/assistants/default_assistant/agents/8863563220075693869` |

---

## 2. Deployed Agent Fleet & A2A Agent Card URLs

### 2.1 Vertex AI Agent Runtime Agents (SPIFFE Principal Identity)

#### 1. **Alex — Root Virtual Product Manager (`vpm-agent`)**
- **Role**: Executive Product Orchestrator ("Mimic Cursor" Multi-File Workspace + Antigravity Skills + HITL Gatekeeper)
- **Model & Thinking Config**: `gemini-3.8-flash` (`thinking_level="MEDIUM"`, `temperature=0.1`)
- **Agent Runtime Resource ID**:
  ```text
  projects/121190797389/locations/us-central1/reasoningEngines/8155381483301765120
  ```
- **A2A Agent Card URL**:
  ```text
  https://us-central1-aiplatform.googleapis.com/reasoningEngines/v1/projects/121190797389/locations/us-central1/reasoningEngines/8155381483301765120/api/a2a/app/.well-known/agent-card.json
  ```
- **SPIFFE Principal Identity**:
  ```text
  principal://agents.global.org-526625392936.system.id.goog/resources/aiplatform/projects/121190797389/locations/us-central1/reasoningEngines/8155381483301765120
  ```
- **Console URL**:
  `https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/us-central1/agent-engines/8155381483301765120?project=vertexai-l300-capstone`

#### 2. **Morgan — Deep Research & FinOps Analyst (`finops-agent`)**
- **Role**: Vendor Evaluation Matrix, 3-Year TCO Modeling ($2M Build vs. $500k Buy), Token Sensitivity & Routing Roi
- **Model & Thinking Config**: `gemini-3.5-flash-lite` (`thinking_level="LOW"`, `temperature=0.0`)
- **Agent Runtime Resource ID**:
  ```text
  projects/121190797389/locations/us-central1/reasoningEngines/1052078971031650304
  ```
- **A2A Agent Card URL**:
  ```text
  https://us-central1-aiplatform.googleapis.com/reasoningEngines/v1/projects/121190797389/locations/us-central1/reasoningEngines/1052078971031650304/api/a2a/app/.well-known/agent-card.json
  ```
- **SPIFFE Principal Identity**:
  ```text
  principal://agents.global.org-526625392936.system.id.goog/resources/aiplatform/projects/121190797389/locations/us-central1/reasoningEngines/1052078971031650304
  ```
- **Console URL**:
  `https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/us-central1/agent-engines/1052078971031650304?project=vertexai-l300-capstone`

---

### 2.2 Google Cloud Run Specialist Agents (Service Account Identity + A2A JSON-RPC)

#### 3. **Marcus — Enterprise Architecture & Zero-Trust Compliance Specialist (`syf-arch-agent`)**
- **Role**: PCI-DSS v4.0, CareCredit HIPAA, FFIEC Auditability, AWS OpenShift (ROSA) ↔ GCP Interconnect & Dual-DLP Gateway Validation
- **Model & Thinking Config**: `gemini-3.5-flash-lite` (`thinking_level="LOW"`, `temperature=0.0`)
- **Cloud Run Service URL**:
  ```text
  https://syf-arch-agent-121190797389.us-central1.run.app
  ```
- **A2A Agent Card URL**:
  ```text
  https://syf-arch-agent-121190797389.us-central1.run.app/a2a/app/.well-known/agent-card.json
  ```
- **A2A JSON-RPC Invocation Endpoint**:
  ```text
  https://syf-arch-agent-121190797389.us-central1.run.app/a2a/app
  ```
- **Runtime Service Account**:
  `syf-arch-agent-sa@vertexai-l300-capstone.iam.gserviceaccount.com`

#### 4. **Devin — Lead Platform Developer & SDLC Scaffolder (`syf-dev-agent`)**
- **Role**: OpenShift UBI9 (`UID 1001`) FastAPI OTel + Cloud DLP Interceptor Scaffolder, Bitbucket Branch/PR Generator, Bidirectional Blocker Sync
- **Model & Thinking Config**: `gemini-3.5-flash-lite` (`thinking_level="LOW"`, `temperature=0.0`)
- **Cloud Run Service URL**:
  ```text
  https://syf-dev-agent-121190797389.us-central1.run.app
  ```
- **A2A Agent Card URL**:
  ```text
  https://syf-dev-agent-121190797389.us-central1.run.app/a2a/app/.well-known/agent-card.json
  ```
- **A2A JSON-RPC Invocation Endpoint**:
  ```text
  https://syf-dev-agent-121190797389.us-central1.run.app/a2a/app
  ```
- **Runtime Service Account**:
  `syf-dev-agent-sa@vertexai-l300-capstone.iam.gserviceaccount.com`

---

## 3. Enterprise MCP Server (`syf-mcp-server`)

| Property | Value |
| :--- | :--- |
| **Cloud Run Service Name** | `syf-mcp-server` |
| **Streamable HTTP MCP Endpoint** | `https://syf-mcp-server-121190797389.us-central1.run.app/mcp` |
| **Health Check Endpoint** | `https://syf-mcp-server-121190797389.us-central1.run.app/healthz` |
| **Auth Provider Resource** | `projects/vertexai-l300-capstone/locations/us-central1/authProviders/syf-mcp-auth-provider` |
| **Exposed Tools (12)** | `list_workspace_documents`, `get_workspace_document`, `patch_document_section`, `query_syf_architecture_catalog`, `calculate_llm_eval_tco`, `validate_pci_hipaa_guardrails`, `create_jira_epic_and_stories`, `assign_jira_ticket_to_squad`, `publish_confluence_spec`, `create_bitbucket_branch_and_pr`, `scaffold_openshift_eval_service`, `sync_sdlc_ticket_blocker` |

---

## 4. Quick Commands for Governance Project Registration (Colleague Handoff)

### 4.1 Register Cloud Run A2A Agents in Agent Registry / Gemini App
```bash
# Register Marcus (Architecture Agent) via A2A Agent Card URL
agents-cli publish gemini \
  --registration-type a2a \
  --agent-card-url "https://syf-arch-agent-121190797389.us-central1.run.app/a2a/app/.well-known/agent-card.json" \
  --gemini-app-id "<TARGET_GEMINI_APP_ID>" \
  --display-name "SYF Architecture & Compliance Agent (Marcus)"

# Register Devin (Developer & SDLC Agent) via A2A Agent Card URL
agents-cli publish gemini \
  --registration-type a2a \
  --agent-card-url "https://syf-dev-agent-121190797389.us-central1.run.app/a2a/app/.well-known/agent-card.json" \
  --gemini-app-id "<TARGET_GEMINI_APP_ID>" \
  --display-name "SYF Developer & SDLC Agent (Devin)"
```

### 4.2 Cross-Project IAM Grants Required When Binding External Agent Gateway
If the governance project (`<GOV_PROJECT_NUMBER>`) invokes these agents through an external **Agent Gateway**:
```bash
# Grant Cloud Run Invoker to Governance Project's Discovery Engine / Gateway SA
for SVC in syf-arch-agent syf-dev-agent syf-mcp-server; do
  gcloud run services add-iam-policy-binding $SVC \
    --project=vertexai-l300-capstone \
    --region=us-central1 \
    --member="serviceAccount:service-<GOV_PROJECT_NUMBER>@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
done

# Grant Vertex AI User to Governance Project SA for Agent Runtime invocation
gcloud projects add-iam-policy-binding vertexai-l300-capstone \
  --member="serviceAccount:service-<GOV_PROJECT_NUMBER>@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```
