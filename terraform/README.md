# Terraform Infrastructure-as-Code (`terraform/`)

Declarative Google Cloud foundation for the **Synchrony Financial Virtual Product Manager (VPM)** multi-agent platform.

> **Note on Hybrid Provisioning**: Terraform provisions all foundational Google Cloud resources (APIs, IAM Service Accounts, Artifact Registry, Secret Manager containers, the versioned GCS Living Workspace Bucket seeded with `seed_data/`, `workspace_artifacts/`, and `shared_skills/`, plus optional Cloud Run v2 services). Python ADK 2.0 `Workflow` agents deployed to **Vertex AI Agent Runtime (`ReasoningEngine`)** (`vpm-agent`, `finops-agent`, `dev-agent`) are packaged and deployed via `agents-cli deploy` (see the root [`README.md`](../README.md)).

---

## 1. Resources Provisioned

| File | Provisioned Resources |
| :--- | :--- |
| [`versions.tf`](./versions.tf) | Terraform `>= 1.6.0` + `hashicorp/google` and `hashicorp/google-beta` (`~> 6.0`). |
| [`main.tf`](./main.tf) | • **11 Google Cloud APIs** (`aiplatform`, `run`, `cloudbuild`, `artifactregistry`, `storage`, `secretmanager`, `discoveryengine`, `agentidentity`, `agentidentitycredentials`, `iamcredentials`, `sts`)<br>• **Least-Privilege IAM Service Accounts**: `syf-mcp-server-sa` and `syf-agent-runtime-sa` + IAM bindings<br>• **Artifact Registry**: `${var.region}-docker.pkg.dev/${var.project_id}/syf-vpm-containers`<br>• **GCS Living Workspace Bucket**: `gs://<project_id>-syf-vpm-workspace` automatically seeded with `seed_data/*.json`, `workspace_artifacts/*`, and `shared_skills/**`<br>• **Secret Manager Secrets**: `syf-mcp-api-key`, `syf-atlassian-api-token`, `syf-bitbucket-access-token`<br>• **Optional Cloud Run v2 Services** (`deploy_cloud_run_services = true`): `syf-mcp-server` and `syf-arch-agent` |
| [`variables.tf`](./variables.tf) | Parameterized project, region, Gemini model IDs, GCS bucket, and non-secret Atlassian/Bitbucket identifiers. |
| [`outputs.tf`](./outputs.tf) | Project number, GCS workspace URI, Artifact Registry URI, service account emails, and Cloud Run URLs. |

---

## 2. Quick Start

```bash
cd terraform

# 1. Copy example variables and populate your GCP project & SDLC identifiers
cp terraform.tfvars.example terraform.tfvars

# 2. Authenticate with Google Cloud ADC
gcloud auth application-default login

# 3. Initialize, validate, and apply foundational GCP infrastructure
terraform init
terraform plan
terraform apply
```

### Optional: Manage Cloud Run Services via Terraform
Once you build and push container images for `syf-mcp-server` and `arch-agent` to Artifact Registry:

```bash
PROJECT_ID="$(terraform output -raw workspace_bucket_name | sed 's/-syf-vpm-workspace//')"
AR_REPO="$(terraform output -raw artifact_registry_repository)"

gcloud builds submit ../syf-mcp-server --tag "${AR_REPO}/syf-mcp-server:latest"
gcloud builds submit ../arch-agent     --tag "${AR_REPO}/syf-arch-agent:latest"

terraform apply \
  -var="deploy_cloud_run_services=true" \
  -var="mcp_server_image=${AR_REPO}/syf-mcp-server:latest" \
  -var="arch_agent_image=${AR_REPO}/syf-arch-agent:latest"
```
