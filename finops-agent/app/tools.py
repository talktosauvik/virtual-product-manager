"""Tools and Agent Identity Auth Manager wiring for Morgan (finops-agent)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from google.adk.auth.credential_manager import CredentialManager
from google.adk.integrations.agent_identity import (
    GcpAuthProvider,
    GcpAuthProviderScheme,
)
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.cloud import storage

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "vertexai-l300-capstone")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
BUCKET_NAME = os.environ.get(
    "SYF_WORKSPACE_BUCKET", f"{PROJECT_ID}-syf-vpm-workspace"
)
SYF_MCP_URL = os.environ.get(
    "SYF_MCP_URL",
    "https://syf-mcp-server-121190797389.us-central1.run.app/mcp",
)
SYF_MCP_AUTH_PROVIDER_URI = os.environ.get(
    "SYF_MCP_AUTH_PROVIDER_URI",
    f"projects/{PROJECT_ID}/locations/{REGION}/authProviders/syf-mcp-auth-provider",
)

# Register Lab 3 Agent Identity Auth Manager Provider (resolves via SPIFFE principal on Agent Runtime!)
CredentialManager.register_auth_provider(GcpAuthProvider())
syf_auth_scheme = GcpAuthProviderScheme(name=SYF_MCP_AUTH_PROVIDER_URI)

SKILLS_DIR = Path(__file__).parent / "skills"


def build_finops_mcp_toolset() -> McpToolset:
    """Create McpToolset authenticated via Lab 3 GcpAuthProviderScheme (SPIFFE principal on Agent Runtime)."""
    toolset: McpToolset | None = None

    def finops_header_provider(readonly_ctx: Any) -> dict[str, str]:
        fallback_key = os.environ.get(
            "SYF_MCP_API_KEY", "syf-enterprise-secret-key-2026"
        )
        try:
            if toolset and toolset.get_auth_config():
                auth_config = toolset.get_auth_config()
                cred = None
                if readonly_ctx and hasattr(readonly_ctx, "get_credential"):
                    cred = readonly_ctx.get_credential(auth_config.credential_key)
                if not cred:
                    cred = auth_config.exchanged_auth_credential
                if cred and cred.http:
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
        except Exception as exc:
            logger.warning("SPIFFE Auth provider header lookup fallback: %s", exc)
        return {"Authorization": f"Bearer {fallback_key}"}

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
    else:
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
