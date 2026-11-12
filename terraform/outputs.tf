output "project_number" {
  description = "Numeric Google Cloud project number."
  value       = data.google_project.current.number
}

output "workspace_bucket_name" {
  description = "Name of the GCS Living Workspace bucket."
  value       = google_storage_bucket.workspace.name
}

output "workspace_bucket_uri" {
  description = "gs:// URI of the GCS Living Workspace bucket."
  value       = "gs://${google_storage_bucket.workspace.name}"
}

output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository URI."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}"
}

output "mcp_server_service_account" {
  description = "Service account email for syf-mcp-server."
  value       = google_service_account.mcp_server_sa.email
}

output "agent_runtime_service_account" {
  description = "Service account email for SYF multi-agent runtime services."
  value       = google_service_account.agent_runtime_sa.email
}

output "syf_mcp_server_url" {
  description = "Deployed Cloud Run URL for syf-mcp-server (when deploy_cloud_run_services = true)."
  value       = length(google_cloud_run_v2_service.syf_mcp_server) > 0 ? google_cloud_run_v2_service.syf_mcp_server[0].uri : "Deploy via gcloud run deploy or set deploy_cloud_run_services = true"
}

output "arch_agent_url" {
  description = "Deployed Cloud Run URL for syf-arch-agent (when deploy_cloud_run_services = true)."
  value       = length(google_cloud_run_v2_service.arch_agent) > 0 ? google_cloud_run_v2_service.arch_agent[0].uri : "Deploy via agents-cli deploy or set deploy_cloud_run_services = true"
}
