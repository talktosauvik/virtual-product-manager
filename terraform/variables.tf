variable "project_id" {
  description = "Google Cloud Project ID hosting Vertex AI Agent Runtime, Cloud Run, and GCS Workspace."
  type        = string
}

variable "region" {
  description = "Primary Google Cloud region for Cloud Run, Artifact Registry, and Vertex AI Agent Runtime."
  type        = string
  default     = "us-central1"
}

variable "genai_location" {
  description = "Vertex AI Gemini model routing location (e.g., global)."
  type        = string
  default     = "global"
}

variable "workspace_bucket_name" {
  description = "GCS bucket name for living PRD/ADR/Backlog workspace artifacts and Synchrony seed data. Defaults to <project_id>-syf-vpm-workspace when empty."
  type        = string
  default     = ""
}

variable "artifact_registry_repo_id" {
  description = "Artifact Registry Docker repository ID for Cloud Run services."
  type        = string
  default     = "syf-vpm-containers"
}

variable "deploy_cloud_run_services" {
  description = "Set to true after building/pushing syf-mcp-server and arch-agent container images to manage Cloud Run v2 services via Terraform."
  type        = bool
  default     = false
}

variable "mcp_server_image" {
  description = "Container image URI for syf-mcp-server (used when deploy_cloud_run_services = true)."
  type        = string
  default     = ""
}

variable "arch_agent_image" {
  description = "Container image URI for syf-arch-agent (used when deploy_cloud_run_services = true)."
  type        = string
  default     = ""
}

variable "model_name" {
  description = "Primary Gemini model identifier for specialist agents."
  type        = string
  default     = "gemini-3-flash-preview"
}

variable "specialist_model_name" {
  description = "Lightweight Gemini model identifier for fast sub-tasks and search grounding."
  type        = string
  default     = "gemini-3.5-flash-lite"
}

variable "atlassian_domain" {
  description = "Atlassian Cloud tenant domain (e.g., my-demo-team.atlassian.net)."
  type        = string
  default     = ""
}

variable "atlassian_email" {
  description = "Atlassian Cloud account email used for Confluence & Jira API calls."
  type        = string
  default     = ""
}

variable "confluence_space_key" {
  description = "Target Confluence Cloud space key for PRD-AI-EVAL-101 and ADR-001-Eval-Gateway."
  type        = string
  default     = "SD"
}

variable "jira_project_key" {
  description = "Target Jira Cloud project key."
  type        = string
  default     = "SYF"
}

variable "jira_epic_key" {
  description = "Master Jira Epic key anchoring Sprint 1 stories."
  type        = string
  default     = "SYF-5"
}

variable "bitbucket_workspace" {
  description = "Bitbucket Cloud workspace slug."
  type        = string
  default     = ""
}

variable "bitbucket_repo_slug" {
  description = "Bitbucket Cloud repository slug for Devin's 8-file gateway commits and PRs."
  type        = string
  default     = "syf-eval-gateway"
}
