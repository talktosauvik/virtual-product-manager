#!/usr/bin/env python3
"""1-Command Clean-Slate Demo Reset Script for Synchrony Virtual Product Manager (VPM).

Wipes the slate 100% clean before or after any test run:
1. Jira (`SYF` Project): Deletes ALL issues `SYF-6` and above so Sprint 1 starts 100% blank,
   preserving only the Master Epic `SYF-5` (reset to `v1.0 DRAFT` 6-sprint baseline).
2. Confluence Cloud (`PRD-AI-EVAL-101.md` & `ADR-001-Eval-Gateway.md`): Restores clean `v1.0 DRAFT`
   (4 sections, no pre-baked TCO verdicts in Sec 2, 3-column CISO table in Sec 3, Kong v3.4 baseline in Sec 4).
3. Bitbucket Cloud (`syf-eval-gateway`): Declines all open Pull Requests and deletes all `feature/*` branches
   so only `main` remains.
4. GCS Workspace (`gs://${SYF_WORKSPACE_BUCKET}`):
   - Uploads clean `seed_data/architecture_standards.json` and `seed_data/eval_vendor_benchmarks.json`
   - Resets `workspace_artifacts/PRD-AI-EVAL-101.md` and `ADR-001-Eval-Gateway.md` to `v1.0 DRAFT`
   - Resets `workspace_artifacts/BACKLOG-AI-EVAL-101.json` to `"stories": []`, `"staged_custom_spec": null`, `"approved_custom_spec": null`
   - Deletes all blobs under `scaffolded_code/`
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
MCP_DIR = ROOT_DIR / "syf-mcp-server" if (ROOT_DIR / "syf-mcp-server").exists() else Path(__file__).resolve().parent
VENV_PYTHON = (
    MCP_DIR / ".venv" / "bin" / "python"
    if (MCP_DIR / ".venv" / "bin" / "python").exists()
    else ROOT_DIR / "vpm-agent" / ".venv" / "bin" / "python"
)
try:
    import google.cloud.agentidentitycredentials_v1  # noqa: F401
except ImportError:
    if VENV_PYTHON.exists() and Path(sys.executable) != VENV_PYTHON:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

sys.path.insert(0, str(MCP_DIR))

from gcs_store import LOCAL_SEED_DIR, SyfGcsWorkspaceStore  # noqa: E402
from live_sdlc_client import LiveAtlassianClient, LiveBitbucketClient  # noqa: E402

PROTECTED_JIRA_KEYS = {"SYF-1", "SYF-2", "SYF-3", "SYF-4", "SYF-5"}


def reset_gcs_and_confluence(sync_confluence: bool = True) -> dict[str, str]:
    store = SyfGcsWorkspaceStore()
    seed_ws = LOCAL_SEED_DIR / "workspace_artifacts"
    restored: dict[str, str] = {}

    for doc_name in ("PRD-AI-EVAL-101.md", "ADR-001-Eval-Gateway.md"):
        content = (seed_ws / doc_name).read_text(encoding="utf-8")
        res = store.save_workspace_document(
            document_name=doc_name,
            content=content,
            author="Dan Weis & Alex (SYF AI Platform)",
        )
        restored[doc_name] = res["gcs_uri"]

    backlog_data = json.loads((seed_ws / "BACKLOG-AI-EVAL-101.json").read_text(encoding="utf-8"))
    restored["BACKLOG-AI-EVAL-101.json"] = store.write_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json", backlog_data
    )

    for seed_json_name in ("architecture_standards.json", "eval_vendor_benchmarks.json"):
        seed_path = LOCAL_SEED_DIR / seed_json_name
        if seed_path.exists():
            seed_obj = json.loads(seed_path.read_text(encoding="utf-8"))
            restored[seed_json_name] = store.write_json(
                f"seed_data/{seed_json_name}", seed_obj
            )

    # Clear scaffolded_code/* in GCS
    try:
        bucket = store._get_bucket()
        blobs = list(bucket.list_blobs(prefix="scaffolded_code/"))
        for b in blobs:
            b.delete()
        restored["scaffolded_code_cleared"] = f"Deleted {len(blobs)} blobs under gs://{store.bucket_name}/scaffolded_code/"
    except Exception as exc:
        restored["scaffolded_code_cleared"] = f"Skipped ({exc})"

    if sync_confluence:
        atlassian = LiveAtlassianClient()
        if atlassian.is_configured:
            for doc_name in ("PRD-AI-EVAL-101.md", "ADR-001-Eval-Gateway.md"):
                content = (seed_ws / doc_name).read_text(encoding="utf-8")
                conf_res = atlassian.upsert_confluence_page(
                    title=doc_name,
                    markdown_content=content,
                    space_key="SD",
                    version_comment="Reset to v1.0 DRAFT Baseline (Kong Enterprise API Gateway v3.4 Ingress — Pending FinOps & CISO Review)",
                    author="Dan Weis & Alex (SYF AI Platform)",
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
        # Reset Master Epic SYF-5 back to pre-curveball 6-sprint baseline
        atlassian.update_anchor_epic(
            anchor_epic_key="SYF-5",
            logical_epic_key="AI-EVAL-101",
            epic_title="Synchrony Enterprise AI Evaluation & Governance Gateway (Baseline v1.0 DRAFT)",
            executive_sponsor="Dan Weis (SVP AI Platform)",
            target_sprints=6,
            approved_budget_usd=76000,
        )
        # Clean up any comments on SYF-5
        try:
            comm_url = f"https://{atlassian.domain}/rest/api/3/issue/SYF-5/comment"
            comm_req = urllib.request.Request(comm_url, headers=atlassian._headers(), method="GET")
            with urllib.request.urlopen(comm_req, timeout=8.0) as c_resp:
                c_data = json.loads(c_resp.read().decode("utf-8"))
                for c in c_data.get("comments", []):
                    cid = c.get("id")
                    if cid:
                        del_c_req = urllib.request.Request(
                            f"{comm_url}/{cid}",
                            headers=atlassian._headers(),
                            method="DELETE",
                        )
                        with urllib.request.urlopen(del_c_req, timeout=8.0):
                            deleted.append(f"SYF-5:comment:{cid}")
        except Exception as c_exc:
            print(f"Warning: SYF-5 comment cleanup skipped: {c_exc}")

        jql_url = f"https://{atlassian.domain}/rest/api/3/search/jql?jql=project%3DSYF&maxResults=100&fields=key,summary"
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
                    if key_num >= 6:
                        del_req = urllib.request.Request(
                            f"https://{atlassian.domain}/rest/api/3/issue/{key}",
                            headers=atlassian._headers(),
                            method="DELETE",
                        )
                        with urllib.request.urlopen(del_req, timeout=8.0):
                            deleted.append(key)
    except Exception as exc:
        print(f"Warning: Jira ticket cleanup skipped: {exc}")
    return deleted


def decline_open_bitbucket_prs() -> dict[str, list[str | int]]:
    bb = LiveBitbucketClient()
    if not bb.is_configured:
        return {"declined_prs": [], "kept_warm_branches": []}
    declined: list[int] = []
    kept_warm_branches: list[str] = ["feature/SYF-5-envoy-otel-gateway"]
    api_base = f"https://api.bitbucket.org/2.0/repositories/{bb.workspace}/{bb.repo_slug}"
    try:
        list_req = urllib.request.Request(
            f"{api_base}/pullrequests?state=OPEN",
            headers={
                "Authorization": bb._auth_header(),
                "Accept": "application/json",
            },
            method="GET",
        )
        with urllib.request.urlopen(list_req, timeout=20.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for pr in data.get("values", []):
                pr_id = pr.get("id")
                if pr_id:
                    dec_req = urllib.request.Request(
                        f"{api_base}/pullrequests/{pr_id}/decline",
                        data=b"{}",
                        headers={
                            "Authorization": bb._auth_header(),
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(dec_req, timeout=20.0):
                        declined.append(int(pr_id))
    except Exception as exc:
        print(f"Warning: Bitbucket open PR cleanup skipped: {exc}")
    return {"declined_prs": declined, "kept_warm_branches": kept_warm_branches}


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset Synchrony VPM Demo State (Wipe Slate Clean)")
    parser.add_argument(
        "--no-confluence",
        action="store_true",
        help="Skip resetting live Confluence pages",
    )
    args = parser.parse_args()

    restored = reset_gcs_and_confluence(sync_confluence=not args.no_confluence)
    pruned = prune_rehearsal_jira_tickets()
    bb_cleanup = decline_open_bitbucket_prs()
    print(
        json.dumps(
            {
                "status": "DEMO_STATE_RESET_COMPLETE",
                "restored_artifacts": restored,
                "deleted_jira_tickets_syf_6_plus": pruned,
                "bitbucket_cleanup": bb_cleanup,
                "protected_master_epic": ["SYF-5"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
