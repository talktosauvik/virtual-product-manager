#!/usr/bin/env bash
set -euo pipefail

export PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-vertexai-l300-capstone}"
export REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
export BUCKET_NAME="${PROJECT_ID}-syf-vpm-workspace"
export SYF_MCP_API_KEY="${SYF_MCP_API_KEY:-syf-enterprise-secret-key-2026}"
export AUTH_PROVIDER_ID="syf-mcp-auth-provider"
export WORKSPACE_ROOT="/home/admin_/vertexai-l300-capstone/virtual-product-manager"

echo "=== [1/4] Configuring GCP Project (${PROJECT_ID}) & Enabling APIs ==="
gcloud config set project "${PROJECT_ID}"
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  discoveryengine.googleapis.com \
  agentidentity.googleapis.com \
  agentidentitycredentials.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  --project="${PROJECT_ID}"

echo "=== [2/4] Creating & Seeding GCS Workspace Bucket (gs://${BUCKET_NAME}) ==="
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
fi

# Upload seed_data JSONs
gcloud storage cp \
  "${WORKSPACE_ROOT}/syf-mcp-server/seed_data/"*.json \
  "gs://${BUCKET_NAME}/seed_data/"

# Upload initial Cursor-style living workspace_artifacts
gcloud storage cp \
  "${WORKSPACE_ROOT}/syf-mcp-server/seed_data/workspace_artifacts/"* \
  "gs://${BUCKET_NAME}/workspace_artifacts/"

# Upload all 6 Synchrony Domain Skills to gs://${BUCKET_NAME}/skills/
gcloud storage cp --recursive \
  "${WORKSPACE_ROOT}/shared_skills/"* \
  "gs://${BUCKET_NAME}/skills/"

echo "=== [3/4] Creating Agent Identity Auth Manager Provider (${AUTH_PROVIDER_ID}) ==="
if ! gcloud alpha agent-identity auth-providers describe "${AUTH_PROVIDER_ID}" \
  --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud alpha agent-identity auth-providers create "${AUTH_PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --api-key="${SYF_MCP_API_KEY}" \
    --description="Synchrony Financial Enterprise MCP Auth Provider (Lab 3 APEX013)"
else
  echo "Auth Provider ${AUTH_PROVIDER_ID} already exists."
fi

echo "=== [4/4] Granting Developer Account roles/agentidentity.user on ${AUTH_PROVIDER_ID} ==="
ACTIVE_ACCOUNT="$(gcloud config get-value account)"
gcloud alpha agent-identity auth-providers add-iam-policy-binding "${AUTH_PROVIDER_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --member="user:${ACTIVE_ACCOUNT}" \
  --role="roles/agentidentity.user" >/dev/null

# Also grant default compute service account access for Cloud Run / local builds
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
gcloud alpha agent-identity auth-providers add-iam-policy-binding "${AUTH_PROVIDER_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/agentidentity.user" >/dev/null

echo "=== Phase 1 Complete! ==="
echo "AUTH_PROVIDER_URI=projects/${PROJECT_ID}/locations/${REGION}/authProviders/${AUTH_PROVIDER_ID}"
gcloud storage ls "gs://${BUCKET_NAME}/**"
