data "google_project" "current" {
  project_id = var.project_id
}

locals {
  bucket_name = var.workspace_bucket_name != "" ? var.workspace_bucket_name : "${var.project_id}-syf-vpm-workspace"

  required_apis = toset([
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "discoveryengine.googleapis.com",
    "agentidentity.googleapis.com",
    "agentidentitycredentials.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ])

  seed_json_files = fileset("${path.module}/../syf-mcp-server/seed_data", "*.json")
  workspace_files = fileset("${path.module}/../syf-mcp-server/seed_data/workspace_artifacts", "*")
  skill_files     = fileset("${path.module}/../shared_skills", "**")
}

# ============================================================================
# 1. Enable Required Google Cloud APIs
# ============================================================================
resource "google_project_service" "apis" {
  for_each           = local.required_apis
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# ============================================================================
# 2. Dedicated Least-Privilege IAM Service Accounts
# ============================================================================
resource "google_service_account" "mcp_server_sa" {
  account_id   = "syf-mcp-server-sa"
  display_name = "SYF Enterprise FastMCP Server Service Account"
  description  = "Identity for syf-mcp-server on Cloud Run accessing GCS Workspace, Auth Manager, and Secret Manager."
  depends_on   = [google_project_service.apis]
}

resource "google_service_account" "agent_runtime_sa" {
  account_id   = "syf-agent-runtime-sa"
  display_name = "SYF Multi-Agent Fleet Runtime Service Account"
  description  = "Identity for SYF specialist agents invoking Vertex AI Gemini, Cloud Run A2A, and FastMCP."
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "mcp_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.mcp_server_sa.email}"
}

resource "google_project_iam_member" "mcp_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.mcp_server_sa.email}"
}

resource "google_project_iam_member" "agent_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_runtime_sa.email}"
}

resource "google_project_iam_member" "agent_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.agent_runtime_sa.email}"
}

resource "google_project_iam_member" "agent_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.agent_runtime_sa.email}"
}

# ============================================================================
# 3. Artifact Registry Docker Repository
# ============================================================================
resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = var.artifact_registry_repo_id
  description   = "Container images for SYF VPM Cloud Run services (syf-mcp-server, syf-arch-agent)"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# ============================================================================
# 4. GCS Living Workspace Bucket & Automated Seed Artifacts
# ============================================================================
resource "google_storage_bucket" "workspace" {
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "mcp_workspace_admin" {
  bucket = google_storage_bucket.workspace.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.mcp_server_sa.email}"
}

resource "google_storage_bucket_iam_member" "agent_workspace_admin" {
  bucket = google_storage_bucket.workspace.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.agent_runtime_sa.email}"
}

resource "google_storage_bucket_object" "seed_jsons" {
  for_each     = local.seed_json_files
  name         = "seed_data/${each.value}"
  bucket       = google_storage_bucket.workspace.name
  source       = "${path.module}/../syf-mcp-server/seed_data/${each.value}"
  content_type = "application/json"
}

resource "google_storage_bucket_object" "workspace_artifacts" {
  for_each = local.workspace_files
  name     = "workspace_artifacts/${each.value}"
  bucket   = google_storage_bucket.workspace.name
  source   = "${path.module}/../syf-mcp-server/seed_data/workspace_artifacts/${each.value}"
  content_type = endswith(each.value, ".json") ? "application/json" : "text/markdown"
}

resource "google_storage_bucket_object" "shared_skills" {
  for_each = local.skill_files
  name     = "skills/${each.value}"
  bucket   = google_storage_bucket.workspace.name
  source   = "${path.module}/../shared_skills/${each.value}"
}

# ============================================================================
# 5. Secret Manager Containers (Populated Out-of-Band — Never in State/Git)
# ============================================================================
resource "google_secret_manager_secret" "mcp_api_key" {
  secret_id = "syf-mcp-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "atlassian_api_token" {
  secret_id = "syf-atlassian-api-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "bitbucket_access_token" {
  secret_id = "syf-bitbucket-access-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# ============================================================================
# 6. Cloud Run v2 Services (syf-mcp-server & syf-arch-agent)
# ============================================================================
resource "google_cloud_run_v2_service" "syf_mcp_server" {
  count    = var.deploy_cloud_run_services && var.mcp_server_image != "" ? 1 : 0
  name     = "syf-mcp-server"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.mcp_server_sa.email

    containers {
      image = var.mcp_server_image

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT_NUMBER"
        value = data.google_project.current.number
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.genai_location
      }
      env {
        name  = "GOOGLE_CLOUD_REGION"
        value = var.region
      }
      env {
        name  = "MODEL"
        value = var.model_name
      }
      env {
        name  = "SPECIALIST_MODEL"
        value = var.specialist_model_name
      }
      env {
        name  = "SYF_WORKSPACE_BUCKET"
        value = google_storage_bucket.workspace.name
      }
      env {
        name  = "ATLASSIAN_DOMAIN"
        value = var.atlassian_domain
      }
      env {
        name  = "ATLASSIAN_EMAIL"
        value = var.atlassian_email
      }
      env {
        name  = "CONFLUENCE_SPACE_KEY"
        value = var.confluence_space_key
      }
      env {
        name  = "JIRA_PROJECT_KEY"
        value = var.jira_project_key
      }
      env {
        name  = "JIRA_EPIC_KEY"
        value = var.jira_epic_key
      }
      env {
        name  = "BITBUCKET_WORKSPACE"
        value = var.bitbucket_workspace
      }
      env {
        name  = "BITBUCKET_REPO_SLUG"
        value = var.bitbucket_repo_slug
      }
      env {
        name  = "AUTH_PROVIDER_URI"
        value = "projects/${data.google_project.current.number}/locations/${var.region}/authProviders/syf-mcp-auth-provider"
      }
      env {
        name  = "ATLASSIAN_AUTH_PROVIDER_URI"
        value = "projects/${data.google_project.current.number}/locations/${var.region}/authProviders/atlassian-cloud-auth-provider"
      }
      env {
        name  = "BITBUCKET_AUTH_PROVIDER_URI"
        value = "projects/${data.google_project.current.number}/locations/${var.region}/authProviders/bitbucket-cloud-auth-provider"
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "mcp_public_invoker" {
  count    = var.deploy_cloud_run_services && var.mcp_server_image != "" ? 1 : 0
  name     = google_cloud_run_v2_service.syf_mcp_server[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "arch_agent" {
  count    = var.deploy_cloud_run_services && var.arch_agent_image != "" ? 1 : 0
  name     = "syf-arch-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_runtime_sa.email

    containers {
      image = var.arch_agent_image

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT_NUMBER"
        value = data.google_project.current.number
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.genai_location
      }
      env {
        name  = "MODEL"
        value = var.model_name
      }
      env {
        name  = "SYF_WORKSPACE_BUCKET"
        value = google_storage_bucket.workspace.name
      }
      env {
        name  = "SYF_MCP_URL"
        value = var.deploy_cloud_run_services && var.mcp_server_image != "" ? "${google_cloud_run_v2_service.syf_mcp_server[0].uri}/mcp" : ""
      }
      env {
        name  = "AUTH_PROVIDER_URI"
        value = "projects/${data.google_project.current.number}/locations/${var.region}/authProviders/syf-mcp-auth-provider"
      }
    }
  }

  depends_on = [google_project_service.apis]
}
