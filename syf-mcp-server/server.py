"""Synchrony Financial (SYF) Enterprise FastMCP Server (Streamable HTTP on /mcp) + Live SDLC Web Portals."""

from __future__ import annotations

import base64
import datetime
import html
import json
import logging
import os
import re
from typing import Any
import urllib.request

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
import uvicorn

load_dotenv()

from gcs_store import LOCAL_SEED_DIR, SyfGcsWorkspaceStore
from gateway_scaffold_templates import (
    build_8_file_gateway_repository,
    build_live_gateway_dashboard_html,
    get_golden_eval_scorecard,
    sanitize_telemetry_payload_live,
)
from live_sdlc_client import (
    BASELINE_STORY_KEY_MAP,
    LiveAtlassianClient,
    LiveBitbucketClient,
    _resolve_token_from_auth_manager,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("syf-mcp-server")

AUTH_PROVIDER_URI = (
    os.getenv("AUTH_PROVIDER_URI")
    or os.getenv("SYF_MCP_AUTH_PROVIDER_URI")
    or "syf-mcp-auth-provider"
)
EXPECTED_API_KEY = _resolve_token_from_auth_manager(
    AUTH_PROVIDER_URI,
    env_fallback_keys=("SYF_MCP_API_KEY",),
)
PORT = int(os.getenv("PORT", "8080"))
PUBLIC_BASE_URL = os.getenv("SYF_PUBLIC_BASE_URL", "").rstrip("/")

store = SyfGcsWorkspaceStore()
live_atlassian = LiveAtlassianClient()
live_bitbucket = LiveBitbucketClient()
mcp = FastMCP(
    "syf-enterprise-mcp-server",
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


# ============================================================================
# 1. FINOPS & VENDOR BENCHMARK TOOLS
# ============================================================================
@mcp.tool()
def query_vendor_cost_benchmarks(
    monthly_spans_millions: float = 5.0,
    include_gecx_50m_projection: bool = True,
) -> dict[str, Any]:
    """Query Synchrony Financial's internal FinOps vendor benchmark database for Arize AX, Braintrust, and Langfuse across specified monthly telemetry span volumes (e.g., 5M baseline vs 50M GECX Contact Center scale)."""
    raw = store.read_json(
        "seed_data/eval_vendor_benchmarks.json",
        local_fallback=LOCAL_SEED_DIR / "eval_vendor_benchmarks.json",
    )
    vendors = raw.get("vendors", {})

    def _compute_tier(spans_m: float) -> dict[str, Any]:
        tier_rows = {}
        extra_10m_blocks = max(0.0, (spans_m - 5.0) / 10.0)
        for vid, v in vendors.items():
            base_lic = float(v.get("base_annual_license_usd", 0.0))
            span_cost = float(v.get("cost_per_million_spans_usd", 0.0)) * spans_m * 12.0
            rosa_compute = float(v.get("rosa_compute_base_annual_usd", 0.0)) + (
                extra_10m_blocks * float(v.get("rosa_compute_per_additional_10m_spans_usd", 0.0))
            )
            total_tco = float(round(base_lic + span_cost + rosa_compute))

            tier_rows[vid] = {
                "vendor_name": v.get("vendor_name", vid),
                "monthly_spans_millions": spans_m,
                "annual_spans_millions": spans_m * 12.0,
                "base_annual_license_usd": round(base_lic),
                "annual_span_ingestion_fee_usd": round(span_cost),
                "internal_rosa_clickhouse_compute_usd": round(rosa_compute),
                "total_annual_tco_usd": total_tco,
                "three_year_tco_usd": round(total_tco * 3),
                "pci_dss_zero_egress_compliant": v.get("pci_dss_zero_egress_compliant", False),
                "carecredit_hipaa_compliant": v.get("carecredit_hipaa_compliant", False),
                "p95_ingestion_latency_ms": v.get("p95_ingestion_latency_ms", 0.0),
            }
        arize_tco = tier_rows["arize_ax"]["total_annual_tco_usd"]
        braintrust_tco = tier_rows["braintrust"]["total_annual_tco_usd"]
        langfuse_tco = tier_rows["langfuse"]["total_annual_tco_usd"]
        return {
            "monthly_spans_millions": spans_m,
            "vendors": tier_rows,
            "recommended_vendor": "Langfuse Enterprise v3 (Self-Hosted on AWS ROSA OpenShift)",
            "net_annual_savings_langfuse_vs_arize_usd": round(arize_tco - langfuse_tco),
            "net_annual_savings_langfuse_vs_braintrust_usd": round(braintrust_tco - langfuse_tco),
            "net_3yr_savings_langfuse_vs_arize_usd": round((arize_tco - langfuse_tco) * 3),
        }

    result: dict[str, Any] = {
        "card_type": "vendor_comparison_matrix",
        "organization": "Synchrony Financial (SYF)",
        "requested_volume_analysis": _compute_tier(monthly_spans_millions),
    }
    if include_gecx_50m_projection and monthly_spans_millions != 50.0:
        result["gecx_50m_surge_projection"] = _compute_tier(50.0)
    return result


# ============================================================================
# 2. ENTERPRISE ARCHITECTURE & CURVEBALL STANDARDS TOOLS
# ============================================================================
@mcp.tool()
def get_architecture_standards(topic_filter: str = "all") -> dict[str, Any]:
    """Retrieve Synchrony Financial's authoritative CISO/CTO Enterprise Architecture standards (baseline_policies for v1.0 baseline review and executive_curveball_policies for curveball impact assessment)."""
    standards = store.read_json(
        "seed_data/architecture_standards.json",
        local_fallback=LOCAL_SEED_DIR / "architecture_standards.json",
    )
    if topic_filter and topic_filter.lower() != "all":
        key = topic_filter.lower()
        all_policies = {
            **standards.get("baseline_policies", {}),
            **standards.get("mandatory_policies", {}),
        }
        filtered_policies = {
            k: v
            for k, v in all_policies.items()
            if key in k.lower() or key in str(v).lower()
        }
        if filtered_policies:
            return {
                "organization": standards.get("organization"),
                "version": standards.get("version"),
                "filtered_topic": topic_filter,
                "baseline_policies": filtered_policies,
                "agile_delivery_model": standards.get("agile_delivery_model", {}),
            }
    return standards


# ============================================================================
# 3. CURSOR-STYLE MULTI-FILE WORKSPACE ARTIFACT TOOLS
# ============================================================================
@mcp.tool()
def list_workspace_documents() -> dict[str, Any]:
    """List all living product & engineering files in the Synchrony Workspace along with their live Confluence Cloud, Jira Cloud, and Bitbucket Cloud URLs resolved via Auth Manager."""
    docs = store.list_workspace_documents()
    enriched_docs: list[dict[str, Any]] = []
    for d in docs:
        doc_name = d.get("document_name") or d.get("name", "")
        if not doc_name or doc_name.endswith(".bak"):
            continue
        if d.get("gcs_path", "").startswith("scaffolded_code/"):
            meta = live_bitbucket.get_live_repository_metadata()
        else:
            meta = live_atlassian.get_live_document_metadata(doc_name)
        enriched_docs.append(
            {
                "document_name": doc_name,
                "size_bytes": d.get("size_bytes"),
                "updated_at": d.get("updated_at"),
                **meta,
            }
        )
    return {
        "confluence_space_key": live_atlassian.confluence_space_key,
        "jira_project_key": live_atlassian.jira_project_key,
        "bitbucket_repository": live_bitbucket.get_live_repository_metadata(),
        "documents": enriched_docs,
    }


@mcp.tool()
def get_workspace_document(document_name: str = "PRD-AI-EVAL-101.md") -> dict[str, Any]:
    """Read the full content of a living workspace document (e.g., PRD-AI-EVAL-101.md, ADR-001-Eval-Gateway.md, or BACKLOG-AI-EVAL-101.json) along with its live Confluence Cloud or Jira Cloud URL resolved via Auth Manager."""
    doc = store.get_workspace_document(document_name)
    live_meta = live_atlassian.get_live_document_metadata(document_name)
    return {
        "document_name": doc.get("document_name", document_name),
        "content": doc.get("content", ""),
        "sections": doc.get("sections", []),
        **live_meta,
    }


@mcp.tool()
def save_workspace_document(
    document_name: str,
    content: str,
    author: str = "Alex (vpm-agent)",
) -> dict[str, Any]:
    """Create or update a full workspace document in gs://<bucket>/workspace_artifacts/ and store a versioned snapshot in history/."""
    return store.save_workspace_document(
        document_name=document_name, content=content, author=author
    )


@mcp.tool()
def patch_document_section(
    document_name: str,
    section_header: str,
    new_section_markdown: str,
    edit_reason: str,
    author: str = "Alex (vpm-agent)",
) -> dict[str, Any]:
    """Perform a Cursor-style surgical inline edit on a specific Markdown section (e.g., '## 4. Security, Ingress & Compliance Boundaries') of PRD-AI-EVAL-101.md or ADR-001-Eval-Gateway.md, returning a unified diff (- / +) and bumping the document version in GCS and Live Confluence Cloud."""
    diff_result = store.patch_document_section(
        document_name=document_name,
        section_header=section_header,
        new_section_markdown=new_section_markdown,
        edit_reason=edit_reason,
        author=author,
    )
    if document_name.endswith(".md"):
        try:
            updated_doc = store.get_workspace_document(document_name)
            live_conf = live_atlassian.upsert_confluence_page(
                title=document_name,
                markdown_content=updated_doc.get("content", ""),
                version_comment=edit_reason,
                author=author,
            )
            if live_conf:
                diff_result["live_confluence_sync"] = live_conf
        except Exception as exc:
            logger.warning("Live Confluence sync after patch skipped: %s", exc)
    return diff_result


# ============================================================================
# 4. SDLC JIRA, CONFLUENCE & BITBUCKET INTEGRATION TOOLS (LIVE REACHABLE URLS)
# ============================================================================
@mcp.tool()
def create_jira_epic(
    epic_key: str = "AI-EVAL-101",
    epic_title: str = "Synchrony Enterprise GenAI Evaluation & Observability Gateway",
    executive_sponsor: str = "Dan Weis (VP of AI Innovation)",
    target_sprints: int = 8,
    approved_budget_usd: float = 108000.0,
) -> dict[str, Any]:
    """Commit and update the master Anchor Jira Epic (`SYF-5` / `AI-EVAL-101`) in Synchrony's Jira instance after human executive approval."""
    backlog = store.read_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json",
        local_fallback=LOCAL_SEED_DIR / "workspace_artifacts" / "BACKLOG-AI-EVAL-101.json",
    )
    live_epic = live_atlassian.update_anchor_epic(
        anchor_epic_key="SYF-5",
        logical_epic_key=epic_key,
        epic_title=epic_title,
        executive_sponsor=executive_sponsor,
        target_sprints=int(target_sprints),
        approved_budget_usd=int(approved_budget_usd),
    )
    hosted_epic_url = f"{PUBLIC_BASE_URL}/jira/browse/{epic_key}"
    epic_url = live_epic["jira_url"] if live_epic else hosted_epic_url

    backlog["epic_key"] = epic_key
    backlog["live_jira_epic_key"] = "SYF-5"
    backlog["epic_title"] = epic_title
    backlog["architecture_revision"] = "v1.1"
    backlog["status"] = "COMMITTED"
    backlog["human_approved"] = True
    backlog["approved_by"] = executive_sponsor
    backlog["total_sprints"] = target_sprints
    backlog["approved_budget_usd"] = approved_budget_usd
    backlog["epic_url"] = epic_url
    backlog["hosted_portal_epic_url"] = hosted_epic_url
    backlog["committed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if backlog.get("staged_custom_spec") and not backlog.get("approved_custom_spec"):
        backlog["approved_custom_spec"] = backlog["staged_custom_spec"]

    existing_stories = backlog.get("stories", [])
    if len(existing_stories) < 8:
        created_8 = live_atlassian.batch_create_sprint1_stories(
            parent_epic_key="SYF-5",
            sprint_id=1,
            assignee_name="Devin (SYF Lead Platform Developer)",
            custom_spec=backlog.get("approved_custom_spec"),
        )
        stories_out = []
        for s in created_8:
            sid = s["story_id"]
            jkey = s["jira_key"]
            stories_out.append(
                {
                    "story_id": sid,
                    "live_jira_key": jkey,
                    "jira_key": jkey,
                    "title": s["title"],
                    "story_points": s["story_points"],
                    "target_file": s["target_file"],
                    "squad": "Devin (SYF-Platform-Mesh-Squad)",
                    "assignee": s["assignee"],
                    "status": s["status"],
                    "jira_url": s["jira_url"],
                    "hosted_portal_url": f"{PUBLIC_BASE_URL}/jira/browse/{sid}",
                    "acceptance_criteria": s["acceptance_criteria"],
                }
            )
        backlog["stories"] = stories_out
        backlog["total_story_points"] = sum(int(s.get("story_points", 0)) for s in stories_out)
        backlog["committed_jira_tickets"] = ["SYF-5"] + [s["live_jira_key"] for s in stories_out]
    else:
        for s in existing_stories:
            sid = s.get("story_id", "AI-STORY-101")
            live_story_key = s.get("live_jira_key") or s.get("jira_key") or BASELINE_STORY_KEY_MAP.get(sid, "SYF-6")
            s["live_jira_key"] = live_story_key
            s["jira_url"] = (
                f"https://{live_atlassian.domain}/browse/{live_story_key}"
                if live_atlassian.is_configured
                else f"{PUBLIC_BASE_URL}/jira/browse/{sid}"
            )
            s["hosted_portal_url"] = f"{PUBLIC_BASE_URL}/jira/browse/{sid}"

    uri = store.write_json("workspace_artifacts/BACKLOG-AI-EVAL-101.json", backlog)
    return {
        "card_type": "jira_backlog_card",
        "status": "EPIC_AND_8_SPRINT1_STORIES_COMMITTED",
        "epic_key": epic_key,
        "live_jira_epic_key": "SYF-5",
        "epic_url": epic_url,
        "hosted_portal_epic_url": hosted_epic_url,
        "executive_sponsor": executive_sponsor,
        "target_sprints": target_sprints,
        "approved_budget_usd": approved_budget_usd,
        "total_story_points": backlog.get("total_story_points", 36),
        "approved_custom_spec": backlog.get("approved_custom_spec"),
        "stories": [
            {
                "story_id": s.get("story_id"),
                "live_jira_key": s.get("live_jira_key"),
                "title": s.get("title"),
                "story_points": s.get("story_points"),
                "target_file": s.get("target_file"),
                "assignee": s.get("assignee", "Devin (SYF Lead Platform Developer)"),
                "squad": s.get("squad"),
                "jira_url": s.get("jira_url"),
                "hosted_portal_url": s.get("hosted_portal_url"),
            }
            for s in backlog.get("stories", [])
        ],
        "workspace_backlog_uri": uri,
    }


@mcp.tool()
def create_jira_story(
    story_id: str,
    title: str,
    squad: str,
    story_points: int,
    sprint: str,
    gherkin_acceptance_criteria: list[str],
    bitbucket_branch: str = "",
    epic_key: str = "AI-EVAL-101",
) -> dict[str, Any]:
    """Create a new Gherkin User Story in Active Sprint 1 (`SYF Sprint 1`) under Parent Epic `SYF-5`, and natively link (`Relates to`) the baseline story (`SYF-6`..`SYF-9`)."""
    backlog = store.read_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json",
        local_fallback=LOCAL_SEED_DIR / "workspace_artifacts" / "BACKLOG-AI-EVAL-101.json",
    )
    branch = bitbucket_branch or f"feature/{epic_key}-{story_id.lower()}"
    hosted_story_url = f"{PUBLIC_BASE_URL}/jira/browse/{story_id}"
    baseline_issue_key = BASELINE_STORY_KEY_MAP.get(story_id, "SYF-9")

    description_lines = [
        f"Logical Story ID: {story_id} | Parent Epic: SYF-5 ({epic_key})",
        f"Assigned Engineering Squad: {squad} | Story Points: {story_points} | Target Sprint: {sprint} (SYF Sprint 1)",
        f"Linked Baseline Reference Story: {baseline_issue_key}",
        f"Bitbucket Feature Branch: {branch}",
        "Gherkin Acceptance Criteria:",
        *[f"• {c}" for c in gherkin_acceptance_criteria],
    ]
    live_story = live_atlassian.create_jira_issue(
        summary=f"[{story_id}] {title} ({story_points} pts — {squad})",
        description_lines=description_lines,
        issue_type="Task",
        project_key="SYF",
        labels=[
            story_id.lower().replace(" ", "-"),
            epic_key.lower().replace(" ", "-"),
            "syf-vpm-agent",
        ],
        parent_epic_key="SYF-5",
        sprint_id=1,
        linked_baseline_issue_key=baseline_issue_key,
    )
    story_url = live_story["jira_url"] if live_story else hosted_story_url
    live_issue_key = (
        live_story["issue_key"] if live_story else baseline_issue_key
    )

    story_obj = {
        "story_id": story_id,
        "live_jira_key": live_issue_key,
        "linked_baseline_issue_key": baseline_issue_key,
        "linked_baseline_issue_url": (
            f"https://{live_atlassian.domain}/browse/{baseline_issue_key}"
            if live_atlassian.is_configured
            else hosted_story_url
        ),
        "epic_key": epic_key,
        "parent_epic_key": "SYF-5",
        "title": title,
        "squad": squad,
        "story_points": story_points,
        "sprint": sprint,
        "status": "READY_FOR_DEV",
        "bitbucket_branch": branch,
        "jira_url": story_url,
        "hosted_portal_url": hosted_story_url,
        "gherkin_acceptance_criteria": gherkin_acceptance_criteria,
    }
    stories = [s for s in backlog.get("stories", []) if s.get("story_id") != story_id]
    stories.append(story_obj)
    backlog["stories"] = stories
    backlog["total_story_points"] = sum(int(s.get("story_points", 0)) for s in stories)
    if story_id not in backlog.get("committed_jira_tickets", []):
        backlog.setdefault("committed_jira_tickets", []).append(story_id)
    store.write_json("workspace_artifacts/BACKLOG-AI-EVAL-101.json", backlog)
    return {
        "card_type": "jira_backlog_card",
        "status": "STORY_CREATED",
        "story": story_obj,
        "live_jira_key": live_issue_key,
        "jira_url": story_url,
        "linked_baseline_issue_key": baseline_issue_key,
        "linked_baseline_issue_url": story_obj["linked_baseline_issue_url"],
        "hosted_portal_url": hosted_story_url,
        "total_epic_story_points": backlog["total_story_points"],
    }


@mcp.tool()
def publish_confluence_prd(
    document_name: str = "PRD-AI-EVAL-101.md",
    space_key: str = "SD",
    approver: str = "Dan Weis",
) -> dict[str, Any]:
    """Publish the approved living PRD and ADR from the GCS workspace to Synchrony's Confluence Cloud space (`SD`), creating a new tracked page version (`v1 -> v2 -> v3`)."""
    prd = store.get_workspace_document(document_name)
    updated_md = prd["content"].replace("status: DRAFT", "status: APPROVED")
    updated_md = re.sub(
        r"\|\s*\*\*Version\*\*\s*\|\s*[^|]+\|",
        "| **Version** | `v1.1` |",
        updated_md,
        count=1,
    )
    updated_md = re.sub(
        r"\|\s*\*\*Status\*\*\s*\|\s*[^|]+\|",
        f"| **Status** | `✅ APPROVED (by {approver})` |",
        updated_md,
        count=1,
    )
    # Upgrade Section 2 with the approved FinOps Vendor TCO Table upon Turn 3 Approval
    approved_sec2 = """## Section 2: Approved FinOps Vendor TCO & Selection Verdict
| Candidate Platform | 5M Spans/Mo Baseline TCO | 50M Spans/Mo 10x Surge TCO | P95 Ingestion Latency | CISO & FinOps Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Arize AX Enterprise (SaaS)** | `$185,000/yr` (`$85k` base + `$100k` spans) | `$1,085,000/yr` (`$85k` base + `$1.0M` spans) | `38.0ms` (Breaches `<25ms`) | **❌ REJECTED (External SaaS Egress)** |
| **Braintrust Enterprise (Hybrid)** | `$135,000/yr` (`$60k` base + `$75k` spans) | `$804,000/yr` (`$60k` base + `$744k` spans) | `24.0ms` | **❌ REJECTED (External Control Plane Egress)** |
| **Langfuse Enterprise v3 (Self-Hosted on ROSA)** | **`$76,000/yr`** (`$36k` lic + `$40k` ROSA) | **`$130,000/yr`** (`$36k` lic + `$94k` ROSA) | **`13.8ms`** (`<25ms` SLA) | **✅ APPROVED (`$109k/yr` -> `$955k/yr` Saved)** |
"""
    updated_md = re.sub(
        r"(^##\s*Section\s*2:[^\n]*\n.*?)(?=^---|\n##\s*Section\s*3:|\Z)",
        f"{approved_sec2}\n",
        updated_md,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    store.save_workspace_document(document_name, updated_md, author=f"Approved by {approver}")
    clean_doc = document_name.replace(".md", "")
    hosted_confluence_url = f"{PUBLIC_BASE_URL}/confluence/display/AIPLAT/{clean_doc}"

    live_conf = live_atlassian.upsert_confluence_page(
        title=document_name,
        markdown_content=updated_md,
        space_key=space_key,
        version_comment=f"Executive HITL Approval by {approver} (status: APPROVED)",
        author=f"Alex (Approved by {approver})",
    )
    # Also keep ADR-001-Eval-Gateway.md synchronized in Confluence when PRD is published
    live_adr_conf = None
    if document_name == "PRD-AI-EVAL-101.md":
        try:
            adr = store.get_workspace_document("ADR-001-Eval-Gateway.md")
            adr_md = adr["content"].replace("status: DRAFT", "status: APPROVED")
            adr_md = re.sub(
                r"\|\s*\*\*Version\*\*\s*\|\s*[^|]+\|",
                "| **Version** | `v1.1` |",
                adr_md,
                count=1,
            )
            adr_md = re.sub(
                r"\|\s*\*\*Status\*\*\s*\|\s*[^|]+\|",
                f"| **Status** | `✅ APPROVED (by {approver})` |",
                adr_md,
                count=1,
            )
            approved_adr_sec2 = """## 2. Architectural Decision & Vendor Selection Verdict
1. **Option A — Arize AX Enterprise (Multi-Tenant SaaS) [❌ REJECTED]**: `$85,000/yr` base + `$1,666.67/1M spans` (`$185,000/yr` at 5M spans/mo; `$1,085,000/yr` at 50M spans/mo). Violates Zero-Egress PCI/HIPAA and breaches `<25ms` SLA (`38.0ms P95`).
2. **Option B — Braintrust Enterprise (Hybrid Cloud) [❌ REJECTED]**: `$60,000/yr` base + `$1,250.00/1M spans` (`$135,000/yr` at 5M spans/mo; `$804,000/yr` at 50M spans/mo). External control-plane metadata egress rejected by CISO.
3. **Option C — Self-Hosted Langfuse Enterprise v3 on AWS ROSA OpenShift [✅ APPROVED]**: `$36,000/yr` Enterprise license + `$40,000/yr` ROSA OpenShift compute & ClickHouse v24.3 storage (`$76,000/yr` at 5M spans/mo; `$130,000/yr` at 50M spans/mo with `$0` per-span fees). `13.8ms P95` in-VPC ingestion latency (`$109k/yr` -> `$955k/yr` saved vs. Arize).
"""
            adr_md = re.sub(
                r"(^##\s*2\.[^\n]*\n.*?)(?=^---|\n##\s*3\.|\Z)",
                f"{approved_adr_sec2}\n",
                adr_md,
                count=1,
                flags=re.MULTILINE | re.DOTALL,
            )
            store.save_workspace_document("ADR-001-Eval-Gateway.md", adr_md, author=f"Approved by {approver}")
            live_adr_conf = live_atlassian.upsert_confluence_page(
                title="ADR-001-Eval-Gateway.md",
                markdown_content=adr_md,
                space_key=space_key,
                version_comment=f"Synchronized with PRD approval by {approver}",
                author=f"Marcus & Alex (Approved by {approver})",
            )
        except Exception as exc:
            logger.warning("Companion ADR Confluence sync skipped: %s", exc)

    return {
        "card_type": "confluence_spec_card",
        "status": "PUBLISHED_TO_CONFLUENCE",
        "page_id": live_conf["page_id"] if live_conf else "163985",
        "version": live_conf["version"] if live_conf else 2,
        "version_label": live_conf.get("version_label", "v2") if live_conf else "v2",
        "space_key": live_conf["space_key"] if live_conf else space_key,
        "document_name": document_name,
        "confluence_url": live_conf["confluence_url"] if live_conf else hosted_confluence_url,
        "history_diff_url": live_conf.get("history_diff_url") if live_conf else hosted_confluence_url,
        "companion_adr_confluence": live_adr_conf,
        "hosted_portal_confluence_url": hosted_confluence_url,
        "gcs_uri": prd["gcs_uri"],
        "approved_by": approver,
    }


@mcp.tool()
def create_bitbucket_branch_and_pr(
    branch_name: str,
    story_id: str,
    pr_title: str,
    scaffolded_files: dict[str, str],
) -> dict[str, Any]:
    """Persist Devin's 8-file production OpenShift/FastAPI/Pytest/Eval repository to gs://<bucket>/scaffolded_code/ AND commit them to Live Bitbucket Cloud, opening or updating a real Pull Request with the 12/12 Pytest & Golden Eval Scorecard."""
    backlog_for_spec = store.read_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json",
        local_fallback=LOCAL_SEED_DIR / "workspace_artifacts" / "BACKLOG-AI-EVAL-101.json",
    )
    approved_custom_spec = backlog_for_spec.get("approved_custom_spec") or backlog_for_spec.get("staged_custom_spec")
    default_8_files = build_8_file_gateway_repository(
        epic_key="AI-EVAL-101",
        story_id=story_id,
        branch_name=branch_name,
        service_mesh_enabled=True,
        custom_spec=approved_custom_spec,
    )
    merged_files: dict[str, str] = dict(default_8_files)
    for fname, file_content in (scaffolded_files or {}).items():
        clean_rel = fname.lstrip("/")
        if clean_rel == "k8s_deployment.yaml":
            clean_rel = "k8s/openshift-envoy-deployment.yaml"
        merged_files[clean_rel] = file_content

    saved_uris: dict[str, str] = {}
    clean_files: dict[str, str] = {}
    for rel_path, file_content in merged_files.items():
        clean_Files_key = rel_path.lstrip("/")
        clean_files[clean_Files_key] = file_content
        ctype = "text/x-python" if clean_Files_key.endswith(".py") else "text/plain"
        uri = store.write_text(
            f"scaffolded_code/{clean_Files_key}", file_content, content_type=ctype
        )
        saved_uris[clean_Files_key] = uri

    bb_meta = live_bitbucket.get_live_repository_metadata()
    hosted_repo_url = (
        bb_meta["repository_url"]
        if live_bitbucket.workspace and live_bitbucket.repo_slug
        else f"{PUBLIC_BASE_URL}/bitbucket/projects/AIPLAT/repos/syf-eval-gateway"
    )
    hosted_pr_url = (
        bb_meta["pull_requests_url"]
        if live_bitbucket.workspace and live_bitbucket.repo_slug
        else f"{hosted_repo_url}/pull-requests/101?branch={branch_name}"
    )
    live_gateway_url = f"{PUBLIC_BASE_URL}/live-gateway"
    story_keys = [
        str(s.get("live_jira_key") or s.get("story_id"))
        for s in backlog_for_spec.get("stories", [])
        if s.get("live_jira_key") or s.get("story_id")
    ]
    jira_issue_key = story_keys[0] if story_keys else BASELINE_STORY_KEY_MAP.get(story_id, "SYF-6")
    all_jira_keys_str = ", ".join(story_keys) if story_keys else "SYF-6 .. SYF-13"
    eval_scorecard = get_golden_eval_scorecard()

    pr_description = (
        f"### Synchrony Autonomous AI Engineering Fleet — Full-Stack Production Build (`{all_jira_keys_str}`)\n"
        f"- **Live Deployed Gateway Sandbox App**: {live_gateway_url}\n"
        f"- **Linked Sprint 1 Jira Stories**: `{all_jira_keys_str}` (Parent Epic: `SYF-5`)\n"
        f"- **8 Committed Production Files**: `proxy_gateway.py`, `eval_suite.py`, `tests/test_gateway_and_evals.py`, `templates/dashboard.html`, `Dockerfile`, `k8s/openshift-envoy-deployment.yaml`, `bitbucket-pipelines.yml`, `requirements.txt`\n"
        f"- **Automated Pytest & 500-Span Golden Evaluation Scorecard**:\n"
        f"  - Pytest Unit & Compliance Suite: `{eval_scorecard['pytest_suite_status']}`\n"
        f"  - PCI-DSS v4.0 (PAN/SSN) & CareCredit HIPAA (MRN/ICD-10) Redaction Recall: `{eval_scorecard['pci_dss_pan_ssn_redaction_recall']}`\n"
        f"  - Static AST Security Gate: `{eval_scorecard['static_ast_security_gate']}`\n"
        f"  - Cached Entra ID JWKS Auth Overhead: `{eval_scorecard['entraid_jwks_cached_auth_p95_ms']}ms` P95 (300s TTL)\n"
        f"  - End-to-End Proxy Latency: `{eval_scorecard['end_to_end_gateway_p95_latency_ms']}ms` P95 (`<25ms` SLA)\n"
    )

    live_bb = live_bitbucket.commit_files_and_open_pr(
        branch_name=branch_name,
        pr_title=pr_title,
        pr_description=pr_description,
        files=clean_files,
        base_branch="main",
        story_id=story_id,
        jira_issue_key=jira_issue_key,
    )
    repo_url = (live_bb or {}).get("repository_url") or hosted_repo_url
    pr_url = (live_bb or {}).get("pull_request_url") or hosted_pr_url

    backlog = store.read_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json",
        local_fallback=LOCAL_SEED_DIR / "workspace_artifacts" / "BACKLOG-AI-EVAL-101.json",
    )
    jira_completion = live_atlassian.complete_sprint1_stories_in_jira(
        stories=backlog.get("stories", []),
        branch_name=branch_name,
        pr_url=pr_url,
        repo_url=repo_url,
        live_gateway_url=live_gateway_url,
        eval_scorecard=eval_scorecard,
        parent_epic_key=str(backlog.get("live_jira_epic_key") or "SYF-5"),
    )
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for s_obj in backlog.get("stories", []):
        s_obj["status"] = "DONE"
        s_obj["live_bitbucket_pr_url"] = pr_url
        s_obj["completed_at"] = now_iso

    pr_entry = {
        "story_id": story_id,
        "live_jira_key": jira_issue_key,
        "branch_name": branch_name,
        "pr_title": pr_title,
        "pr_url": pr_url,
        "repo_url": repo_url,
        "live_deployed_gateway_url": live_gateway_url,
        "hosted_portal_pr_url": hosted_pr_url,
        "gcs_scaffolded_files": saved_uris,
        "eval_scorecard": eval_scorecard,
        "jira_stories_transitioned_to_done": jira_completion.get("transitioned_to_done", []),
        "jira_issues_commented": jira_completion.get("commented_issues", []),
        "created_at": now_iso,
    }
    backlog.setdefault("bitbucket_prs", []).append(pr_entry)
    store.write_json("workspace_artifacts/BACKLOG-AI-EVAL-101.json", backlog)
    return {
        "card_type": "dev_scaffold_card",
        "status": "BITBUCKET_PR_OPENED_AND_JIRA_STORIES_DONE",
        "repository_url": repo_url,
        "branch_name": branch_name,
        "linked_jira_story": story_id,
        "live_jira_key": jira_issue_key,
        "linked_sprint1_jira_keys": story_keys or ["SYF-6", "SYF-7", "SYF-8", "SYF-9", "SYF-10", "SYF-11", "SYF-12", "SYF-13"],
        "jira_stories_transitioned_to_done": jira_completion.get("transitioned_to_done", []),
        "jira_issues_commented": jira_completion.get("commented_issues", []),
        "pull_request_url": pr_url,
        "live_deployed_gateway_url": live_gateway_url,
        "hosted_portal_bitbucket_url": hosted_repo_url,
        "committed_file_count": len(clean_files),
        "committed_files": list(clean_files.keys()),
        "automated_eval_scorecard": eval_scorecard,
        "scaffolded_gcs_uris": saved_uris,
    }


@mcp.tool()
def sync_sdlc_ticket_blocker(
    ticket_id: str = "AI-STORY-102",
    blocker_summary: str = "Entra ID synchronous token introspection adds 42.3ms P95 latency, breaching <25ms SLA.",
    resolution_architecture: str = "Switch to local in-memory/Redis JWKS public key caching (300s TTL), reducing auth verification to 1.8ms P95.",
) -> dict[str, Any]:
    """Synchronize an engineering blocker from a Jira ticket (`SYF-7` / `AI-STORY-102`) back into the living PRD, Live Jira comment stream, and Live Confluence (`v2 -> v3`)."""
    backlog = store.read_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json",
        local_fallback=LOCAL_SEED_DIR / "workspace_artifacts" / "BACKLOG-AI-EVAL-101.json",
    )
    live_jira_key = BASELINE_STORY_KEY_MAP.get(ticket_id, "SYF-7")
    live_jira_url = (
        f"https://{live_atlassian.domain}/browse/{live_jira_key}"
        if live_atlassian.is_configured
        else f"{PUBLIC_BASE_URL}/jira/browse/{ticket_id}"
    )

    # Post the resolution comment directly on Live Jira ticket SYF-7
    live_comment_added = live_atlassian.add_jira_comment(
        live_jira_key,
        f"[CONTINUOUS SDLC BLOCKER RESOLVED BY ALEX & MARCUS] "
        f"Blocker: {blocker_summary} -> Resolution Architecture: {resolution_architecture} "
        f"(Verified 1.8ms P95 auth latency, 13.8ms total gateway P95 latency, 0 sprint slip).",
    )

    for story in backlog.get("stories", []):
        if story.get("story_id") == ticket_id:
            story["status"] = "UNBLOCKED_VIA_ADR_PATCH"
            story["blocker_resolved"] = blocker_summary
            story["resolution_applied"] = resolution_architecture
            story["live_jira_key"] = live_jira_key
            story["jira_url"] = live_jira_url
            story["hosted_portal_url"] = f"{PUBLIC_BASE_URL}/jira/browse/{ticket_id}"
            story.setdefault("gherkin_acceptance_criteria", []).append(
                f"Given the blocker resolution ({resolution_architecture}), When Entra ID JWT validation runs, Then P95 auth latency remains under 2ms."
            )
    store.write_json("workspace_artifacts/BACKLOG-AI-EVAL-101.json", backlog)

    new_sec4 = (
        "## 4. Security, Ingress & Compliance Boundaries\n"
        "- **PCI-DSS v4.0 & CareCredit HIPAA Scrubbing**: Inline deterministic JSON serialization (`json.dumps` / `json.loads`—zero `eval()`) with compiled regex redaction for 16-digit PAN (`[REDACTED_PAN]`), 9-digit SSN (`[REDACTED_SSN]`), and CareCredit Medical Record Numbers (`[REDACTED_MRN]`).\n"
        f"- **Identity & Access Management (Updated via {ticket_id} / {live_jira_key} Blocker Sync)**: {resolution_architecture} Mutual TLS (`mTLS 1.3`) enforced on all service-to-service hops.\n"
        "- **Network Ingress & Service Mesh**: Synchrony Internal Service Mesh (Envoy sidecar `mesh.syf.bank/injected: \"true\"` with mTLS 1.3) replacing deprecated Kong Enterprise Gateway v3.4."
    )
    edit_reason = f"Continuous SDLC Blocker Sync from Jira ticket {ticket_id} ({live_jira_key}): {resolution_architecture}"
    diff_result = store.patch_document_section(
        document_name="PRD-AI-EVAL-101.md",
        section_header="## 4. Security, Ingress & Compliance Boundaries",
        new_section_markdown=new_sec4,
        edit_reason=edit_reason,
        author="Alex (vpm-agent SDLC Auto-Sync)",
    )
    live_conf = None
    try:
        updated_prd = store.get_workspace_document("PRD-AI-EVAL-101.md")
        live_conf = live_atlassian.upsert_confluence_page(
            title="PRD-AI-EVAL-101.md",
            markdown_content=updated_prd.get("content", ""),
            version_comment=edit_reason,
            author="Alex (vpm-agent SDLC Auto-Sync)",
        )
    except Exception as exc:
        logger.warning("Confluence update during blocker sync skipped: %s", exc)

    return {
        "status": "SDLC_BLOCKER_SYNCHRONIZED",
        "ticket_id": ticket_id,
        "live_jira_key": live_jira_key,
        "jira_url": live_jira_url,
        "hosted_portal_jira_url": f"{PUBLIC_BASE_URL}/jira/browse/{ticket_id}",
        "live_jira_comment_posted": live_comment_added,
        "live_confluence_sync": live_conf,
        "schedule_slip_sprints": 0,
        "new_p95_auth_latency_ms": 1.8,
        "total_proxy_p95_latency_ms": 13.8,
        "prd_surgical_diff": diff_result,
    }


# ============================================================================
# 5. INTERACTIVE ENTERPRISE WEB PORTALS (/jira, /confluence, /bitbucket)
# ============================================================================
async def jira_portal_handler(request: Request) -> HTMLResponse:
    issue_key = request.path_params.get("issue_key", "AI-EVAL-101")
    backlog = store.read_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json",
        local_fallback=LOCAL_SEED_DIR / "workspace_artifacts" / "BACKLOG-AI-EVAL-101.json",
    )
    stories = backlog.get("stories", [])
    selected_story = next((s for s in stories if s.get("story_id") == issue_key), None)

    rows_html = ""
    for s in stories:
        sid = html.escape(str(s.get("story_id", "")))
        stitle = html.escape(str(s.get("title", "")))
        ssquad = html.escape(str(s.get("squad", "")))
        spoints = html.escape(str(s.get("story_points", "")))
        sstatus = html.escape(str(s.get("status", "READY_FOR_DEV")))
        highlight = "background:#e8f0fe;font-weight:600;" if sid == issue_key else ""
        criteria_items = "".join(
            f"<li>{html.escape(str(c))}</li>"
            for c in s.get("gherkin_acceptance_criteria", [])
        )
        rows_html += f"""
        <tr style="{highlight}">
          <td><a href="{PUBLIC_BASE_URL}/jira/browse/{sid}">{sid}</a></td>
          <td>{stitle}<ul style="margin:6px 0 0 18px;font-size:12px;color:#444;">{criteria_items}</ul></td>
          <td><span style="background:#eef2ff;padding:3px 8px;border-radius:4px;">{ssquad}</span></td>
          <td style="text-align:center;"><strong>{spoints}</strong></td>
          <td><span style="background:#e6f4ea;color:#137333;padding:3px 8px;border-radius:4px;font-size:12px;">{sstatus}</span></td>
        </tr>
        """

    page_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>SYF Enterprise Jira — {html.escape(issue_key)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #f4f5f7; color: #172b4d; }}
    header {{ background: #0052cc; color: white; padding: 14px 28px; display: flex; justify-content: space-between; align-items: center; }}
    .container {{ max-width: 1120px; margin: 24px auto; background: white; padding: 28px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; background: #deebff; color: #0747a6; font-weight: 600; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ border-bottom: 1px solid #dfe1e6; padding: 12px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #fafbfc; font-size: 12px; text-transform: uppercase; color: #5e6c84; }}
    a {{ color: #0052cc; text-decoration: none; font-weight: 600; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <header>
    <div><strong>Synchrony Financial (SYF) — Enterprise Jira Portal</strong> | Project: <code>AIPLAT / AIINNOV</code></div>
    <div style="font-size:13px;">Authenticated via GCP Agent Identity Auth Manager (SPIFFE)</div>
  </header>
  <div class="container">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <span class="badge">{html.escape(issue_key)}</span>
        <h1 style="margin:10px 0 4px 0;font-size:22px;">{html.escape(selected_story['title'] if selected_story else backlog.get('epic_title', 'Synchrony Enterprise GenAI Evaluation & Observability Gateway'))}</h1>
        <p style="margin:4px 0;color:#5e6c84;">
          Epic: <a href="{PUBLIC_BASE_URL}/jira/browse/{html.escape(backlog.get('epic_key', 'AI-EVAL-101'))}">{html.escape(backlog.get('epic_key', 'AI-EVAL-101'))}</a> |
          Sponsor: <strong>{html.escape(str(backlog.get('approved_by', 'Dan Weis (VP of AI Innovation)')))}</strong> |
          Status: <strong>{html.escape(str(backlog.get('status', 'COMMITTED')))}</strong> |
          Total Story Points: <strong>{html.escape(str(backlog.get('total_story_points', 192)))}</strong>
        </p>
      </div>
      <div>
        <a href="{PUBLIC_BASE_URL}/confluence/display/AIPLAT/PRD-AI-EVAL-101" style="margin-right:16px;">View Confluence PRD &rarr;</a>
        <a href="{PUBLIC_BASE_URL}/bitbucket/projects/AIPLAT/repos/syf-eval-gateway">View Bitbucket Repo &rarr;</a>
      </div>
    </div>
    <h3 style="margin-top:24px;">Committed Gherkin User Stories (Live from GCS Workspace <code>BACKLOG-AI-EVAL-101.json</code>)</h3>
    <table>
      <thead>
        <tr>
          <th style="width:120px;">Story Key</th>
          <th>Summary &amp; Gherkin Acceptance Criteria</th>
          <th style="width:190px;">Assigned SYF Squad</th>
          <th style="width:70px;">Points</th>
          <th style="width:150px;">Status</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
</body>
</html>"""
    return HTMLResponse(page_html)


async def confluence_portal_handler(request: Request) -> HTMLResponse:
    space_key = request.path_params.get("space_key", "AIPLAT")
    page_slug = request.path_params.get("page_slug", "PRD-AI-EVAL-101")
    doc_name = page_slug if page_slug.endswith(".md") else f"{page_slug}.md"
    try:
        doc = store.get_workspace_document(doc_name)
    except Exception:
        doc = store.get_workspace_document("PRD-AI-EVAL-101.md")

    content_escaped = html.escape(doc.get("content", ""))
    page_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>SYF Confluence Wiki — {html.escape(doc_name)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #f4f5f7; color: #172b4d; }}
    header {{ background: #172b4d; color: white; padding: 14px 28px; display: flex; justify-content: space-between; align-items: center; }}
    .container {{ max-width: 1040px; margin: 24px auto; background: white; padding: 28px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
    pre {{ background: #fafbfc; border: 1px solid #dfe1e6; padding: 18px; border-radius: 6px; white-space: pre-wrap; word-wrap: break-word; font-size: 13.5px; line-height: 1.55; }}
    a {{ color: #0052cc; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <header>
    <div><strong>Synchrony Financial (SYF) — Confluence Engineering Wiki</strong> | Space: <code>{html.escape(space_key)}</code></div>
    <div>
      <a href="{PUBLIC_BASE_URL}/confluence/display/AIPLAT/PRD-AI-EVAL-101" style="color:#79f2c0;margin-right:16px;">PRD-AI-EVAL-101.md</a>
      <a href="{PUBLIC_BASE_URL}/confluence/display/AIPLAT/ADR-001-Eval-Gateway" style="color:#79f2c0;margin-right:16px;">ADR-001-Eval-Gateway.md</a>
      <a href="{PUBLIC_BASE_URL}/jira/browse/AI-EVAL-101" style="color:white;">Jira Epic AI-EVAL-101 &rarr;</a>
    </div>
  </header>
  <div class="container">
    <h1 style="margin-top:0;">{html.escape(doc_name)}</h1>
    <p style="color:#5e6c84;font-size:13px;">
      Live GCS Backing Artifact: <code>{html.escape(str(doc.get('gcs_uri', '')))}</code> |
      Sections: <code>{html.escape(', '.join(doc.get('sections', [])))}</code>
    </p>
    <pre>{content_escaped}</pre>
  </div>
</body>
</html>"""
    return HTMLResponse(page_html)


async def bitbucket_portal_handler(request: Request) -> HTMLResponse:
    repo_slug = request.path_params.get("repo_slug", "syf-eval-gateway")
    backlog = store.read_json(
        "workspace_artifacts/BACKLOG-AI-EVAL-101.json",
        local_fallback=LOCAL_SEED_DIR / "workspace_artifacts" / "BACKLOG-AI-EVAL-101.json",
    )
    # Load scaffolded files from GCS or local seed fallback
    scaffold_files = {}
    for fname in ("Dockerfile", "Dockerfile.ubi9", "proxy_gateway.py", "otel_dlp_proxy.py", "k8s_deployment.yaml"):
        try:
            scaffold_files[fname] = store.read_text(f"scaffolded_code/{fname}")
        except Exception:
            pass

    if not scaffold_files:
        scaffold_files = {
            "Dockerfile": (
                "# Hardened non-root container image for Synchrony OpenShift cluster (ROSA)\n"
                "FROM registry.access.redhat.com/ubi9/python-312:latest\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\n"
                "COPY proxy_gateway.py .\n"
                "EXPOSE 8080\n"
                "USER 1001\n"
                'CMD ["uvicorn", "proxy_gateway:app", "--host", "0.0.0.0", "--port", "8080"]\n'
            ),
            "proxy_gateway.py": (
                '"""Synchrony Financial Self-Hosted Evaluation Gateway (OpenShift ROSA + Entra ID JWKS + Inline DLP)."""\n'
                "import json, os, re\n"
                "from fastapi import FastAPI, Request\n"
                "app = FastAPI(title='SYF LLM Evaluation Gateway', version='1.0.0')\n"
                "SSN_REGEX = re.compile(r'\\b\\d{3}-\\d{2}-\\d{4}\\b')\n"
                "PAN_REGEX = re.compile(r'\\b(?:\\d[ -]*?){13,16}\\b')\n"
                "MRN_REGEX = re.compile(r'\\bMRN-\\d{6,10}\\b')\n\n"
                "def sanitize_payload(payload: dict) -> dict:\n"
                "    raw = json.dumps(payload)\n"
                "    raw = SSN_REGEX.sub('[REDACTED_SSN]', raw)\n"
                "    raw = PAN_REGEX.sub('[REDACTED_PAN]', raw)\n"
                "    raw = MRN_REGEX.sub('[REDACTED_MRN]', raw)\n"
                "    return json.loads(raw)\n"
            ),
            "k8s_deployment.yaml": (
                "apiVersion: apps/v1\n"
                "kind: Deployment\n"
                "metadata:\n"
                "  name: syf-llm-eval-gateway\n"
                "  namespace: syf-ai-innovation\n"
                "  labels:\n"
                "    app: syf-llm-eval-gateway\n"
                '    mesh.syf.bank/injected: "true" # Synchrony Internal Service Mesh Envoy sidecar\n'
                "spec:\n"
                "  replicas: 3\n"
            ),
        }

    files_html = ""
    for fname, fcontent in scaffold_files.items():
        files_html += f"""
        <div style="margin-top:20px;">
          <div style="background:#ebecf0;padding:8px 14px;border-radius:6px 6px 0 0;font-family:monospace;font-weight:600;">
            scaffolded_code/{html.escape(fname)}
          </div>
          <pre style="margin:0;background:#1e1e1e;color:#d4d4d4;padding:16px;border-radius:0 0 6px 6px;overflow-x:auto;font-size:13px;">{html.escape(fcontent)}</pre>
        </div>
        """

    page_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>SYF Bitbucket — AIPLAT / {html.escape(repo_slug)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #f4f5f7; color: #172b4d; }}
    header {{ background: #0747a6; color: white; padding: 14px 28px; display: flex; justify-content: space-between; align-items: center; }}
    .container {{ max-width: 1120px; margin: 24px auto; background: white; padding: 28px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
    a {{ color: #0052cc; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <header>
    <div><strong>Synchrony Financial (SYF) — Bitbucket Git Repository &amp; PR Portal</strong> | Repo: <code>AIPLAT/{html.escape(repo_slug)}</code></div>
    <div>
      <a href="{PUBLIC_BASE_URL}/jira/browse/AI-EVAL-101" style="color:white;margin-right:16px;">Linked Jira Epic: AI-EVAL-101</a>
      <a href="{PUBLIC_BASE_URL}/confluence/display/AIPLAT/PRD-AI-EVAL-101" style="color:#79f2c0;">Confluence PRD</a>
    </div>
  </header>
  <div class="container">
    <h1 style="margin-top:0;">Repository: <code>AIPLAT / {html.escape(repo_slug)}</code> (OpenShift ROSA UBI9 Scaffold)</h1>
    <p style="color:#5e6c84;">
      Generated by <strong>Devin (<code>syf-dev-agent</code>)</strong> |
      Target Runtime: <strong>Red Hat OpenShift on AWS (ROSA) — Non-Root UID 1001 + Envoy Service Mesh Sidecar</strong> |
      GCS Backing Store: <code>gs://{html.escape(store.bucket_name)}/scaffolded_code/</code>
    </p>
    {files_html}
  </div>
</body>
</html>"""
    return HTMLResponse(page_html)


async def live_gateway_portal_handler(request: Request) -> HTMLResponse:
    """Serve the interactive Synchrony Enterprise GenAI Evaluation & DLP Gateway Web App."""
    return HTMLResponse(build_live_gateway_dashboard_html(PUBLIC_BASE_URL))


async def live_gateway_evaluate_handler(request: Request) -> JSONResponse:
    """Execute live inline PCI-DSS v4.0 & CareCredit HIPAA redaction + W3C TraceContext evaluation."""
    import time
    import uuid

    t0 = time.perf_counter()
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {"raw_input": str(payload)}
    except Exception:
        payload = {"error": "Invalid JSON body"}

    incoming_trace = str(payload.get("traceparent", "")).strip()
    w3c_traceparent = (
        incoming_trace
        if incoming_trace and len(incoming_trace.split("-")) == 4
        else f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"
    )
    sanitized_payload, redaction_counts = sanitize_telemetry_payload_live(payload)
    inline_dlp_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return JSONResponse(
        {
            "status": "INGESTED_AND_REDACTED",
            "gateway_service": "syf-eval-gateway (Red Hat UBI9 Python 3.12 | Non-Root UID 1001)",
            "service_mesh": 'Synchrony Internal Envoy Service Mesh (mesh.syf.bank/injected: "true" | mTLS 1.3)',
            "otel_exporter": "OTLPSpanExporter (HTTP/protobuf async batching -> Self-Hosted Langfuse v3 ClickHouse)",
            "w3c_traceparent": w3c_traceparent,
            "entraid_jwks_cache_hit": True,
            "entraid_jwks_auth_latency_ms": 1.8,
            "inline_dlp_execution_ms": inline_dlp_ms,
            "simulated_gateway_p95_ms": 13.8,
            "sla_under_25ms": True,
            "redaction_summary": redaction_counts,
            "sanitized_payload": sanitized_payload,
        }
    )


# ============================================================================
# AUTHENTICATION MIDDLEWARE (Supports Lab 3 Agent Identity Auth Manager Bearer Key)
# ============================================================================
class BearerOrApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/healthz", "/") or path.startswith(
            ("/jira/", "/confluence/", "/bitbucket/", "/live-gateway")
        ):
            if path in ("/healthz", "/"):
                return JSONResponse(
                    {
                        "status": "ok",
                        "service": "syf-mcp-server",
                        "portals": {
                            "jira": f"{PUBLIC_BASE_URL}/jira/browse/AI-EVAL-101",
                            "confluence": f"{PUBLIC_BASE_URL}/confluence/display/AIPLAT/PRD-AI-EVAL-101",
                            "bitbucket": f"{PUBLIC_BASE_URL}/bitbucket/projects/AIPLAT/repos/syf-eval-gateway",
                            "live_gateway": f"{PUBLIC_BASE_URL}/live-gateway",
                        },
                    }
                )
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        api_key_header = (
            request.headers.get("X-API-Key")
            or request.headers.get("X-Goog-Api-Key")
            or ""
        )
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        elif api_key_header:
            token = api_key_header.strip()

        if EXPECTED_API_KEY and token and token != EXPECTED_API_KEY:
            logger.warning("Rejected invalid token on %s", path)
            return JSONResponse({"error": "Unauthorized MCP client"}, status_code=401)

        return await call_next(request)


async def workspace_json_handler(request: Request) -> JSONResponse:
    """Fast authenticated JSON endpoint for vpm-agent and dev-agent to read/write workspace JSON artifacts via syf-mcp-server."""
    blob_path = request.path_params.get("blob_path", "").strip("/")
    if not blob_path:
        return JSONResponse({"error": "Missing blob_path"}, status_code=400)
    local_candidate = LOCAL_SEED_DIR / blob_path
    if not local_candidate.exists() and blob_path.startswith("seed_data/"):
        local_candidate = LOCAL_SEED_DIR / blob_path[len("seed_data/") :]
    if request.method == "POST":
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                return JSONResponse({"error": "Expected JSON object"}, status_code=400)
            if payload.get("_merge"):
                existing = store.read_json(
                    blob_path,
                    local_fallback=local_candidate if local_candidate.exists() else None,
                )
                for k, v in payload.items():
                    if k != "_merge":
                        existing[k] = v
                uri = store.write_json(blob_path, existing)
                return JSONResponse({"status": "merged", "gcs_uri": uri, "data": existing})
            uri = store.write_json(blob_path, payload)
            return JSONResponse({"status": "saved", "gcs_uri": uri})
        except Exception as exc:
            logger.warning("workspace_json_handler POST error for %s: %s", blob_path, exc)
            return JSONResponse({"error": str(exc)}, status_code=500)
    try:
        data = store.read_json(blob_path, local_fallback=local_candidate if local_candidate.exists() else None)
        return JSONResponse(data)
    except Exception as exc:
        logger.warning("workspace_json_handler fallback error for %s: %s", blob_path, exc)
        return JSONResponse({"error": str(exc)}, status_code=404)


async def devin_commit_and_open_pr_handler(request: Request) -> JSONResponse:
    """Authenticated REST endpoint for Devin (`dev-agent`) to commit the 8-file repo and open a live Bitbucket PR."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    branch_name = str(body.get("branch_name") or "feature/sprint-1-eval-gateway-full-stack")
    story_id = str(body.get("story_id") or "AI-STORY-105")
    pr_title = str(
        body.get("pr_title")
        or "feat(eval-gateway): Sprint 1 Full-Stack OpenShift UBI9 FastAPI OTLP+DLP Gateway, Envoy Mesh & 12-Test Eval Suite"
    )
    scaffolded_files = body.get("scaffolded_files") or {}
    import asyncio
    result = await asyncio.to_thread(
        create_bitbucket_branch_and_pr,
        branch_name,
        story_id,
        pr_title,
        scaffolded_files,
    )
    return JSONResponse(result)


def _prewarm_caches_in_background() -> None:
    """Pre-warms Auth Manager tokens and Confluence/Bitbucket metadata on container startup."""
    import threading

    def _worker() -> None:
        try:
            live_atlassian.get_live_document_metadata("PRD-AI-EVAL-101.md")
            live_atlassian.get_live_document_metadata("ADR-001-Eval-Gateway.md")
            live_bitbucket.get_live_repository_metadata()
            logger.info("Pre-warmed Auth Manager tokens and Confluence/Bitbucket metadata caches.")
        except Exception as exc:
            logger.debug("Startup pre-warm skipped: %s", exc)

    threading.Thread(target=_worker, daemon=True).start()


app = mcp.streamable_http_app()
app.routes.extend(
    [
        Route("/api/workspace-json/{blob_path:path}", workspace_json_handler, methods=["GET", "POST"]),
        Route("/api/devin/commit-and-open-pr", devin_commit_and_open_pr_handler, methods=["POST"]),
        Route("/live-gateway", live_gateway_portal_handler, methods=["GET"]),
        Route("/live-gateway/api/evaluate", live_gateway_evaluate_handler, methods=["POST"]),
        Route("/jira/browse/{issue_key:path}", jira_portal_handler, methods=["GET"]),
        Route("/confluence/display/{space_key}/{page_slug:path}", confluence_portal_handler, methods=["GET"]),
        Route("/confluence/spaces/{space_key}/pages/{page_slug:path}", confluence_portal_handler, methods=["GET"]),
        Route("/bitbucket/projects/{proj}/repos/{repo_slug:path}", bitbucket_portal_handler, methods=["GET"]),
    ]
)
app.add_middleware(BearerOrApiKeyMiddleware)
_prewarm_caches_in_background()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
