"""Tools and Agent Identity Auth Manager wiring for Morgan (finops-agent)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.adk.auth.credential_manager import CredentialManager
from google.adk.integrations.agent_identity import (
    GcpAuthProvider,
    GcpAuthProviderScheme,
)
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.cloud import storage

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
BUCKET_NAME = os.getenv("SYF_WORKSPACE_BUCKET")
SYF_MCP_URL = os.getenv("SYF_MCP_URL")
AUTH_PROVIDER_URI = (
    os.getenv("AUTH_PROVIDER_NAME")
    or os.getenv("AUTH_PROVIDER_URI")
    or os.getenv("SYF_MCP_AUTH_PROVIDER_URI")
)

# Register Lab 3 Agent Identity Auth Manager Provider
CredentialManager.register_auth_provider(GcpAuthProvider())
syf_auth_scheme = GcpAuthProviderScheme(name=AUTH_PROVIDER_URI) if AUTH_PROVIDER_URI else None

SKILLS_DIR = Path(__file__).parent / "skills"


def _resolve_auth_manager_token(auth_provider_uri: str | None) -> str | None:
    """Resolve credential token directly from GCP Agent Identity Auth Manager if needed."""
    if not auth_provider_uri:
        return None
    try:
        from google.cloud.agentidentitycredentials_v1 import (
            AuthProviderCredentialsServiceClient,
            RetrieveCredentialsRequest,
        )

        client = AuthProviderCredentialsServiceClient(transport="rest")
        resp = client.retrieve_credentials(
            RetrieveCredentialsRequest(
                auth_provider=auth_provider_uri,
                user_id=os.getenv("SYF_AUTH_USER_ID", "syf-vpm-runtime"),
            ),
            timeout=6.0,
        )
        if hasattr(resp, "success") and getattr(resp.success, "token", ""):
            return resp.success.token.strip()
        if getattr(resp, "token", ""):
            return resp.token.strip()
    except Exception as exc:
        logger.debug("agentidentitycredentials_v1 lookup skipped: %s", exc)
    return None


def build_finops_mcp_toolset() -> McpToolset:
    """Create McpToolset authenticated via Lab 3 GcpAuthProviderScheme (SPIFFE principal on Agent Runtime)."""
    toolset: McpToolset | None = None

    def finops_header_provider(readonly_context: Any) -> dict[str, str]:
        try:
            if toolset and toolset.get_auth_config():
                auth_config = toolset.get_auth_config()
                cred = GcpAuthProvider().get_auth_credential(auth_config, readonly_context)
                if not cred and readonly_context and hasattr(readonly_context, "get_credential"):
                    cred = readonly_context.get_credential(auth_config.credential_key)
                if not cred:
                    cred = auth_config.exchanged_auth_credential
                if cred and cred.http:
                    if cred.http.credentials and cred.http.credentials.token:
                        return {"Authorization": f"Bearer {cred.http.credentials.token}"}
                    if cred.http.additional_headers:
                        token = (
                            cred.http.additional_headers.get("X-API-Key")
                            or cred.http.additional_headers.get("X-GOOG-API-KEY")
                        )
                        if token:
                            return {"Authorization": f"Bearer {token}"}
        except Exception as exc:
            logger.debug("GcpAuthProvider credential lookup note: %s", exc)

        token = _resolve_auth_manager_token(AUTH_PROVIDER_URI)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=SYF_MCP_URL),
        auth_scheme=syf_auth_scheme,
        tool_filter=["query_vendor_cost_benchmarks"],
        header_provider=finops_header_provider,
    )
    return toolset


def list_syf_skills() -> dict[str, Any]:
    """List Synchrony Financial domain skills bundled with Morgan (finops-agent)."""
    skills = []
    if SKILLS_DIR.exists():
        for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            skills.append(
                {
                    "skill_name": skill_md.parent.name,
                    "path": str(skill_md.relative_to(SKILLS_DIR.parent)),
                }
            )
    return {"agent": "finops_agent (Morgan)", "available_skills": skills}


def load_syf_skill(skill_name: str, include_references: bool = True) -> dict[str, Any]:
    """Load a Synchrony Financial FinOps SKILL.md runbook and TCO formulas on demand."""
    clean_name = skill_name.strip().lower()
    skill_dir = SKILLS_DIR / clean_name
    skill_file = skill_dir / "SKILL.md"
    content = ""
    refs: dict[str, str] = {}

    if skill_file.exists():
        content = skill_file.read_text(encoding="utf-8")
        if include_references:
            for sub in ("references", "resources"):
                sub_dir = skill_dir / sub
                if sub_dir.exists():
                    for f in sorted(sub_dir.iterdir()):
                        if f.is_file():
                            refs[f"{sub}/{f.name}"] = f.read_text(encoding="utf-8")
    elif BUCKET_NAME:
        try:
            client = storage.Client(project=PROJECT_ID)
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(f"skills/{clean_name}/SKILL.md")
            if blob.exists():
                content = blob.download_as_text(encoding="utf-8")
        except Exception as exc:
            return {"error": f"Skill {clean_name} not found: {exc}"}

    return {
        "skill_name": clean_name,
        "skill_markdown": content,
        "supplementary_files": refs,
    }
