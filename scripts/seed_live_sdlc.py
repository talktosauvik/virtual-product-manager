#!/usr/bin/env python3
"""Turnkey Seeding & Lab 3 Auth Manager Provisioning Script for Live Jira, Confluence, and Bitbucket.

Usage (once credentials are provided):
  export ATLASSIAN_DOMAIN="your-site.atlassian.net"
  export ATLASSIAN_EMAIL="you@example.com"
  export ATLASSIAN_API_TOKEN="<YOUR_ATLASSIAN_API_TOKEN>"
  export JIRA_PROJECT_KEY="AIPLAT"
  export CONFLUENCE_SPACE_KEY="AIPLAT"
  export BITBUCKET_WORKSPACE="your-workspace"
  export BITBUCKET_REPO_SLUG="syf-eval-gateway"
  export BITBUCKET_ACCESS_TOKEN="<YOUR_BITBUCKET_ACCESS_TOKEN>"
  python3 scripts/seed_live_sdlc.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "syf-mcp-server"))

from live_sdlc_client import LiveAtlassianClient, LiveBitbucketClient  # noqa: E402


def main() -> None:
    atlassian = LiveAtlassianClient()
    bitbucket = LiveBitbucketClient()

    seed_dir = ROOT_DIR / "syf-mcp-server" / "seed_data" / "workspace_artifacts"
    prd_path = seed_dir / "PRD-AI-EVAL-101.md"
    adr_path = seed_dir / "ADR-001-Eval-Gateway.md"
    backlog_path = seed_dir / "BACKLOG-AI-EVAL-101.json"

    print("=== 1. Seeding Live Confluence Cloud Pages ===")
    if atlassian.is_configured:
        for doc_path, title in [
            (prd_path, "PRD-AI-EVAL-101: Synchrony Enterprise AI Evaluation Gateway"),
            (adr_path, "ADR-001-Eval-Gateway: Dual-Cloud OpenTelemetry & Zero-PII Architecture"),
        ]:
            if doc_path.exists():
                res = atlassian.upsert_confluence_page(
                    title=title,
                    markdown_content=doc_path.read_text(encoding="utf-8"),
                    version_comment="Initial baseline seeded by SYF VPM Bootstrap",
                )
                print(f"  -> Confluence [{title}]: {json.dumps(res, indent=2)}")
    else:
        print("  [Skipped] Set ATLASSIAN_DOMAIN, ATLASSIAN_EMAIL, and ATLASSIAN_API_TOKEN to seed Confluence.")

    print("\n=== 2. Seeding Live Jira Cloud Epic & Baseline Stories ===")
    if atlassian.is_configured and backlog_path.exists():
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        epic_res = atlassian.create_jira_issue(
            summary=backlog.get("epic_title", "SYF Enterprise AI Evaluation Gateway"),
            description_lines=[
                f"Executive Sponsor: {backlog.get('approved_by', 'Dan Weis')}",
                "Baseline Epic seeded from SYF VPM Workspace.",
            ],
            issue_type="Epic",
            labels=["SYF-AI-Platform", "AI-EVAL-101"],
        )
        print(f"  -> Jira Epic: {json.dumps(epic_res, indent=2)}")
    else:
        print("  [Skipped] Set ATLASSIAN_DOMAIN, ATLASSIAN_EMAIL, and ATLASSIAN_API_TOKEN to seed Jira.")

    print("\n=== 3. Verifying Live Bitbucket Cloud Repository ===")
    if bitbucket.is_configured:
        print(f"  -> Bitbucket configured for https://bitbucket.org/{bitbucket.workspace}/{bitbucket.repo_slug}")
    else:
        print("  [Skipped] Set BITBUCKET_WORKSPACE and BITBUCKET_ACCESS_TOKEN to seed Bitbucket.")


if __name__ == "__main__":
    main()
