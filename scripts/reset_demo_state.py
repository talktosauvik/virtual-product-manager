#!/usr/bin/env python3
"""1-Command Demo Reset Script for Synchrony Virtual Product Manager (VPM).

Restores:
1. GCS Workspace artifacts (`PRD-AI-EVAL-101.md`, `ADR-001-Eval-Gateway.md`, `BACKLOG-AI-EVAL-101.json`)
   back to the clean `v1 (DRAFT)` Kong Enterprise Gateway v3.4 baseline so Turn 2's Cursor-style
   unified diff (`- Kong v3.4` / `+ Synchrony Envoy Service Mesh`) is always fresh.
2. Live Confluence Cloud (`PRD-AI-EVAL-101` page `163985` & `ADR-001-Eval-Gateway` page `131074`)
   back to the `DRAFT` Kong baseline content (incrementing the Confluence page revision cleanly).
3. Optional (`--prune-rehearsal-jira`): Deletes any rehearsal delta Jira tickets (`SYF-10+`) in Project `SYF`
   while strictly preserving the 5 core baseline issues (`SYF-5` Epic and `SYF-6`..`SYF-9` Stories).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import urllib.request

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "syf-mcp-server"))

from gcs_store import LOCAL_SEED_DIR, SyfGcsWorkspaceStore  # noqa: E402
from live_sdlc_client import LiveAtlassianClient  # noqa: E402

PROTECTED_JIRA_KEYS = {"SYF-1", "SYF-2", "SYF-3", "SYF-4", "SYF-5", "SYF-6", "SYF-7", "SYF-8", "SYF-9"}


def reset_gcs_and_confluence(sync_confluence: bool = True) -> dict[str, str]:
    store = SyfGcsWorkspaceStore()
    seed_ws = LOCAL_SEED_DIR / "workspace_artifacts"
    restored: dict[str, str] = {}

    for doc_name in ("PRD-AI-EVAL-101.md", "ADR-001-Eval-Gateway.md"):
        content = (seed_ws / doc_name).read_text(encoding="utf-8")
        res = store.save_workspace_document(
            document_name=doc_name,
            content=content,
            author="Demo Reset Script (Baseline v1 DRAFT — Kong v3.4)",
        )
        restored[doc_name] = res["gcs_uri"]

    backlog_data = json.loads((seed_ws / "BACKLOG-AI-EVAL-101.json").read_text(encoding="utf-8"))
    restored["BACKLOG-AI-EVAL-101.json"] = store.write_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json", backlog_data
    )

    if sync_confluence:
        atlassian = LiveAtlassianClient()
        if atlassian.is_configured:
            for doc_name in ("PRD-AI-EVAL-101.md", "ADR-001-Eval-Gateway.md"):
                content = (seed_ws / doc_name).read_text(encoding="utf-8")
                conf_res = atlassian.upsert_confluence_page(
                    title=doc_name,
                    markdown_content=content,
                    space_key="SD",
                    version_comment="Reset to clean DRAFT Baseline (Kong v3.4 Ingress) for next live demo run",
                    author="Alex (vpm-agent Demo Reset)",
                )
                if conf_res:
                    restored[f"Confluence:{doc_name}"] = (
                        f"{conf_res['confluence_url']} (v{conf_res['version']})"
                    )
    return restored


def prune_rehearsal_jira_tickets() -> list[str]:
    atlassian = LiveAtlassianClient()
    if not atlassian.is_configured:
        return []
    deleted: list[str] = []
    try:
        jql_url = f"https://{atlassian.domain}/rest/api/3/search/jql?jql=project%3DSYF&maxResults=50&fields=key,summary"
        req = urllib.request.Request(jql_url, headers=atlassian._headers(), method="GET")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for issue in data.get("issues", []):
                key = issue.get("key", "")
                if key and key not in PROTECTED_JIRA_KEYS:
                    try:
                        key_num = int(key.split("-")[1])
                    except Exception:
                        continue
                    if key_num >= 10:
                        del_req = urllib.request.Request(
                            f"https://{atlassian.domain}/rest/api/3/issue/{key}",
                            headers=atlassian._headers(),
                            method="DELETE",
                        )
                        with urllib.request.urlopen(del_req, timeout=8.0):
                            deleted.append(key)
    except Exception as exc:
        print(f"Warning: Jira rehearsal ticket prune skipped: {exc}")
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset Synchrony VPM Demo State")
    parser.add_argument(
        "--no-confluence",
        action="store_true",
        help="Skip resetting live Confluence pages",
    )
    parser.add_argument(
        "--prune-rehearsal-jira",
        action="store_true",
        help="Delete rehearsal delta Jira tickets (SYF-10+) while preserving SYF-5..SYF-9",
    )
    args = parser.parse_args()

    restored = reset_gcs_and_confluence(sync_confluence=not args.no_confluence)
    pruned = prune_rehearsal_jira_tickets() if args.prune_rehearsal_jira else []
    print(
        json.dumps(
            {
                "status": "DEMO_STATE_RESET_COMPLETE",
                "restored_artifacts": restored,
                "pruned_rehearsal_jira_tickets": pruned,
                "protected_baseline_jira_tickets": sorted(PROTECTED_JIRA_KEYS - {"SYF-1", "SYF-2", "SYF-3", "SYF-4"}),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
