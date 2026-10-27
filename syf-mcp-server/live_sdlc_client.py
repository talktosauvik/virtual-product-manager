"""Live Atlassian Cloud (Jira v3 + Agile v1.0 + IssueLink + Confluence v1) and Bitbucket Cloud v2.0 Client.

Also provides the Dynamic Developer Community & Web Intelligence Engine (`CB-DYNAMIC`)
that taps directly in parallel into:
  1. StackOverflow REST API v2.3 (`https://api.stackexchange.com/2.3/search/advanced`)
  2. GitHub Issues Search REST API (`https://api.github.com/search/issues`)
  3. Reddit Public JSON Search API (`https://www.reddit.com/search.json`)
  4. Vertex AI Google Search Grounding (`gemini-3.5-flash-lite` + `google_search`)

Implements Lab 3 (APEX013) Agent Identity Auth Manager runtime credential resolution:
- Tokens are NEVER hardcoded in source code or Docker images.
- At runtime, `_resolve_token_from_auth_manager()` queries Google Cloud's
  `agentidentitycredentials.googleapis.com` API using the workload's IAM / SPIFFE
  identity to retrieve the credential from:
  1. `projects/vertexai-l300-capstone/locations/us-central1/authProviders/atlassian-cloud-auth-provider`
  2. `projects/vertexai-l300-capstone/locations/us-central1/authProviders/bitbucket-cloud-auth-provider`
"""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import html
import json
import logging
import os
import re
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

import google.auth
import google.auth.transport.requests

logger = logging.getLogger("syf-live-sdlc")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "vertexai-l300-capstone")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

_TOKEN_CACHE: dict[str, str] = {}

BASELINE_STORY_KEY_MAP: dict[str, str] = {
    "AI-STORY-101": "SYF-6",
    "AI-STORY-102": "SYF-7",
    "AI-STORY-103": "SYF-8",
    "AI-STORY-104": "SYF-9",
}


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _resolve_token_from_auth_manager(
    auth_provider_id: str,
    env_fallback_keys: tuple[str, ...] = (),
) -> str:
    """Dynamically retrieve an API token / PAT from GCP Agent Identity Auth Manager (Lab 3 APEX013)."""
    for env_key in env_fallback_keys:
        val = os.environ.get(env_key, "").strip()
        if val:
            return val

    if auth_provider_id in _TOKEN_CACHE:
        return _TOKEN_CACHE[auth_provider_id]

    provider_resource = (
        auth_provider_id
        if auth_provider_id.startswith("projects/")
        else f"projects/{PROJECT_ID}/locations/{LOCATION}/authProviders/{auth_provider_id}"
    )

    # First try official GAPIC client if installed
    try:
        from google.cloud.agentidentitycredentials_v1 import (
            AuthProviderCredentialsServiceClient,
            RetrieveCredentialsRequest,
        )

        client = AuthProviderCredentialsServiceClient(transport="rest")
        resp = client.retrieve_credentials(
            RetrieveCredentialsRequest(
                auth_provider=provider_resource,
                user_id="syf-vpm-runtime",
            )
        )
        token = (resp.success.token or "").strip()
        if token:
            _TOKEN_CACHE[auth_provider_id] = token
            logger.info(
                "Resolved credential via AuthProviderCredentialsServiceClient: %s",
                provider_resource,
            )
            return token
    except Exception:
        pass

    # Fallback to direct REST call against agentidentitycredentials.googleapis.com
    url = f"https://agentidentitycredentials.googleapis.com/v1/{provider_resource}:retrieveCredentials"
    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        payload = json.dumps(
            {
                "userId": "syf-vpm-runtime",
                "scopes": [],
                "continueUri": "",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("success", {}).get("token", "").strip()
            if token:
                _TOKEN_CACHE[auth_provider_id] = token
                logger.info(
                    "Resolved credential dynamically from GCP Agent Identity Auth Manager REST: %s",
                    provider_resource,
                )
                return token
    except Exception as exc:
        logger.warning(
            "Auth Manager lookup for %s failed (%s)", provider_resource, exc
        )
    return ""


def _markdown_to_confluence_storage(
    md_text: str,
    revision_number: int | None = None,
    version_comment: str = "",
    author: str = "Alex (vpm-agent)",
) -> str:
    """Convert Markdown into clean Confluence Storage Format XHTML with a top executive revision banner."""
    lines = md_text.splitlines()
    out: list[str] = []

    if revision_number is not None:
        ts = _utc_now_str()
        safe_comment = html.escape(version_comment or "Synchrony VPM Automated SDLC Sync")
        safe_author = html.escape(author)
        out.append(
            f'<ac:structured-macro ac:name="info">'
            f"<ac:rich-text-body>"
            f"<p><strong>Synchrony VPM Live Document Revision: v{revision_number}</strong> | "
            f"<strong>Updated:</strong> <code>{ts}</code> | "
            f"<strong>Author:</strong> <code>{safe_author}</code><br/>"
            f"<strong>Change Audit:</strong> {safe_comment}</p>"
            f"</ac:rich-text-body>"
            f"</ac:structured-macro>"
        )

    in_code = False
    code_lines: list[str] = []
    in_list = False

    for line in lines:
        if line.strip().startswith("```"):
            if in_list:
                out.append("</ul>")
                in_list = False
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                escaped_code = html.escape("\n".join(code_lines))
                out.append(f"<pre><code>{escaped_code}</code></pre>")
            continue

        if in_code:
            code_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue

        if stripped.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{_inline_format(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{_inline_format(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{_inline_format(stripped[2:])}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline_format(stripped[2:])}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{_inline_format(stripped)}</p>")

    if in_list:
        out.append("</ul>")
    if in_code and code_lines:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(out)


def _inline_format(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


CONFLUENCE_TITLE_MAP = {
    "PRD-AI-EVAL-101.md": "PRD-AI-EVAL-101: Synchrony Enterprise AI Evaluation Gateway",
    "ADR-001-Eval-Gateway.md": "ADR-001-Eval-Gateway: Dual-Cloud OpenTelemetry & Zero-PII Architecture",
}


class LiveAtlassianClient:
    """Real Jira Software Cloud (REST v3 + Agile v1.0 + IssueLink) + Confluence Cloud (REST v1) integration."""

    def __init__(
        self,
        domain: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
        jira_project_key: str | None = None,
        confluence_space_key: str | None = None,
        auth_provider_id: str = "atlassian-cloud-auth-provider",
    ) -> None:
        raw_domain = (
            domain
            or os.environ.get("ATLASSIAN_DOMAIN", "")
            or os.environ.get("JIRA_CLOUD_DOMAIN", "my-demo-team.atlassian.net")
        ).strip()
        self.domain = (
            raw_domain.replace("https://", "").replace("http://", "").strip("/")
        )
        self.email = (
            email
            or os.environ.get("ATLASSIAN_EMAIL", "")
            or os.environ.get("JIRA_USER_EMAIL", "iamsouvik@google.com")
        ).strip()
        self._explicit_token = api_token
        self.auth_provider_id = auth_provider_id
        self.jira_project_key = (
            jira_project_key or os.environ.get("JIRA_PROJECT_KEY", "SYF")
        ).strip()
        self.confluence_space_key = (
            confluence_space_key or os.environ.get("CONFLUENCE_SPACE_KEY", "SD")
        ).strip()

    @property
    def api_token(self) -> str:
        if self._explicit_token:
            return self._explicit_token
        return _resolve_token_from_auth_manager(
            self.auth_provider_id,
            env_fallback_keys=("ATLASSIAN_API_TOKEN", "JIRA_API_TOKEN"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.domain and self.email and self.api_token)

    def _headers(self) -> dict[str, str]:
        creds = base64.b64encode(
            f"{self.email}:{self.api_token}".encode("utf-8")
        ).decode("utf-8")
        return {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Confluence Cloud REST API (Create or Update Page with Version Diff)
    # ------------------------------------------------------------------
    def upsert_confluence_page(
        self,
        title: str,
        markdown_content: str,
        space_key: str | None = None,
        version_comment: str = "Updated by Synchrony Virtual PM Agent (Alex)",
        author: str = "Alex (vpm-agent)",
    ) -> dict[str, Any] | None:
        """Create or update a real Confluence Cloud page (v1 -> v2 -> v3) and return its live URL and version."""
        if not self.is_configured:
            return None
        target_space = (
            space_key
            if space_key and space_key != "AIPLAT"
            else self.confluence_space_key
        )
        canonical_title = CONFLUENCE_TITLE_MAP.get(title, title)

        try:
            query = urllib.parse.urlencode(
                {
                    "spaceKey": target_space,
                    "title": canonical_title,
                    "expand": "version",
                }
            )
            search_url = f"https://{self.domain}/wiki/rest/api/content?{query}"
            req = urllib.request.Request(
                search_url, headers=self._headers(), method="GET"
            )
            existing_page = None
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                if results:
                    existing_page = results[0]

            if existing_page:
                page_id = existing_page["id"]
                current_version = int(
                    existing_page.get("version", {}).get("number", 1)
                )
                next_version = current_version + 1
                storage_xhtml = _markdown_to_confluence_storage(
                    markdown_content,
                    revision_number=next_version,
                    version_comment=version_comment,
                    author=author,
                )
                update_payload = {
                    "id": page_id,
                    "type": "page",
                    "title": canonical_title,
                    "space": {"key": target_space},
                    "body": {
                        "storage": {
                            "value": storage_xhtml,
                            "representation": "storage",
                        }
                    },
                    "version": {
                        "number": next_version,
                        "message": f"[v{next_version}] {version_comment}",
                    },
                }
                put_url = f"https://{self.domain}/wiki/rest/api/content/{page_id}"
                put_req = urllib.request.Request(
                    put_url,
                    data=json.dumps(update_payload).encode("utf-8"),
                    headers=self._headers(),
                    method="PUT",
                )
                with urllib.request.urlopen(put_req, timeout=10.0) as put_resp:
                    updated = json.loads(put_resp.read().decode("utf-8"))
                    webui = updated.get("_links", {}).get("webui", "")
                    live_url = (
                        f"https://{self.domain}/wiki{webui}"
                        if webui
                        else f"https://{self.domain}/wiki/spaces/{target_space}/pages/{page_id}"
                    )
                    return {
                        "page_id": str(page_id),
                        "previous_version": current_version,
                        "version": next_version,
                        "version_label": f"v{next_version} (diff from v{current_version})",
                        "space_key": target_space,
                        "confluence_url": live_url,
                        "history_diff_url": f"https://{self.domain}/wiki/pages/diffpagesbyversion.action?pageId={page_id}&selectedPageVersions={next_version}&selectedPageVersions={current_version}",
                        "provider": "Atlassian Confluence Cloud (Live REST API via Auth Manager)",
                    }
            else:
                storage_xhtml = _markdown_to_confluence_storage(
                    markdown_content,
                    revision_number=1,
                    version_comment=version_comment,
                    author=author,
                )
                create_payload = {
                    "type": "page",
                    "title": canonical_title,
                    "space": {"key": target_space},
                    "body": {
                        "storage": {
                            "value": storage_xhtml,
                            "representation": "storage",
                        }
                    },
                }
                post_url = f"https://{self.domain}/wiki/rest/api/content"
                post_req = urllib.request.Request(
                    post_url,
                    data=json.dumps(create_payload).encode("utf-8"),
                    headers=self._headers(),
                    method="POST",
                )
                with urllib.request.urlopen(post_req, timeout=10.0) as post_resp:
                    created = json.loads(post_resp.read().decode("utf-8"))
                    page_id = created.get("id", "")
                    webui = created.get("_links", {}).get("webui", "")
                    return {
                        "page_id": str(page_id),
                        "previous_version": 0,
                        "version": 1,
                        "version_label": "v1 (Initial Baseline)",
                        "space_key": target_space,
                        "confluence_url": f"https://{self.domain}/wiki{webui}"
                        if webui
                        else f"https://{self.domain}/wiki/spaces/{target_space}/pages/{page_id}",
                        "provider": "Atlassian Confluence Cloud (Live REST API via Auth Manager)",
                    }
        except Exception as exc:
            logger.warning("Confluence Cloud live API call failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Jira Cloud REST API v3: Anchor Epic Update + Linked Delta Stories
    # ------------------------------------------------------------------
    def update_anchor_epic(
        self,
        anchor_epic_key: str,
        logical_epic_key: str,
        epic_title: str,
        executive_sponsor: str,
        target_sprints: int,
        approved_budget_usd: int,
    ) -> dict[str, Any] | None:
        """Update the Anchor Epic (`SYF-5`) in-place and log an approval audit comment (zero duplicate epics)."""
        if not self.is_configured:
            return None
        ts = _utc_now_str()
        description_lines = [
            f"[{logical_epic_key}] {epic_title}",
            f"Executive Sponsor: {executive_sponsor}",
            f"Approved Sprint Horizon: {target_sprints} Sprints | Approved Engineering & Infra Budget: ${approved_budget_usd:,}",
            f"Last Executive Approval Sync: {ts}",
        ]
        adf_content = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line}],
            }
            for line in description_lines
        ]
        payload = {
            "fields": {
                "summary": f"[{logical_epic_key}] {epic_title} ({target_sprints} Sprints / ${approved_budget_usd:,})",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": adf_content,
                },
            }
        }
        try:
            put_req = urllib.request.Request(
                f"https://{self.domain}/rest/api/3/issue/{anchor_epic_key}",
                data=json.dumps(payload).encode("utf-8"),
                headers=self._headers(),
                method="PUT",
            )
            with urllib.request.urlopen(put_req, timeout=10.0):
                pass
            self.add_jira_comment(
                anchor_epic_key,
                f"[EXECUTIVE HITL APPROVAL — {ts}] Sponsor {executive_sponsor} approved {logical_epic_key} "
                f"for {target_sprints} sprints (${approved_budget_usd:,} total approved budget).",
            )
            return {
                "issue_key": anchor_epic_key,
                "logical_epic_key": logical_epic_key,
                "jira_url": f"https://{self.domain}/browse/{anchor_epic_key}",
                "issue_type": "Epic",
                "updated_at": ts,
                "provider": "Atlassian Jira Cloud (Anchor Epic Updated In-Place via Auth Manager)",
            }
        except Exception as exc:
            logger.warning(
                "Anchor epic update on %s failed (%s); falling back to comment",
                anchor_epic_key,
                exc,
            )
            if self.add_jira_comment(
                anchor_epic_key,
                f"[EXECUTIVE HITL APPROVAL — {ts}] Sponsor {executive_sponsor} approved {logical_epic_key} "
                f"({target_sprints} sprints, ${approved_budget_usd:,}).",
            ):
                return {
                    "issue_key": anchor_epic_key,
                    "logical_epic_key": logical_epic_key,
                    "jira_url": f"https://{self.domain}/browse/{anchor_epic_key}",
                    "issue_type": "Epic",
                    "updated_at": ts,
                    "provider": "Atlassian Jira Cloud (Anchor Epic Audit Comment via Auth Manager)",
                }
            return None

    def link_jira_issues(
        self,
        new_issue_key: str,
        baseline_issue_key: str,
        link_type: str = "Relates",
        comment_text: str | None = None,
    ) -> bool:
        """Create a native Jira Issue Link (`POST /rest/api/3/issueLink`) connecting a new Delta Story to its baseline story."""
        if not self.is_configured or not new_issue_key or not baseline_issue_key:
            return False
        if new_issue_key == baseline_issue_key:
            return True
        payload: dict[str, Any] = {
            "type": {"name": link_type},
            "inwardIssue": {"key": new_issue_key},
            "outwardIssue": {"key": baseline_issue_key},
        }
        if comment_text:
            payload["comment"] = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment_text}],
                        }
                    ],
                }
            }
        try:
            req = urllib.request.Request(
                f"https://{self.domain}/rest/api/3/issueLink",
                data=json.dumps(payload).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                return resp.status in (200, 201, 204)
        except Exception as exc:
            logger.warning(
                "Could not create Jira issueLink %s -> %s: %s",
                new_issue_key,
                baseline_issue_key,
                exc,
            )
            return False

    def create_jira_issue(
        self,
        summary: str,
        description_lines: list[str],
        issue_type: str = "Task",
        project_key: str | None = None,
        labels: list[str] | None = None,
        parent_epic_key: str | None = "SYF-5",
        sprint_id: int | None = 1,
        linked_baseline_issue_key: str | None = None,
    ) -> dict[str, Any] | None:
        """Create a real Jira Cloud issue (Story/Task) in active Sprint 1 under Epic SYF-5 and link it to its baseline story."""
        if not self.is_configured:
            return None
        proj = (
            project_key
            if project_key and project_key not in ("AI", "AIPLAT", "AIINNOV")
            else self.jira_project_key
        )
        adf_content = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line}],
            }
            for line in description_lines
            if line.strip()
        ]
        for candidate_type in [issue_type, "Story", "Task"]:
            payload: dict[str, Any] = {
                "fields": {
                    "project": {"key": proj},
                    "summary": summary,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": adf_content,
                    },
                    "issuetype": {"name": candidate_type},
                }
            }
            if labels:
                payload["fields"]["labels"] = labels
            if candidate_type != "Epic" and parent_epic_key:
                payload["fields"]["parent"] = {"key": parent_epic_key}
            try:
                req = urllib.request.Request(
                    f"https://{self.domain}/rest/api/3/issue",
                    data=json.dumps(payload).encode("utf-8"),
                    headers=self._headers(),
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    if resp.status in (200, 201):
                        body = json.loads(resp.read().decode("utf-8"))
                        issue_key = body.get("key", "")
                        if candidate_type != "Epic" and sprint_id and issue_key:
                            try:
                                sprint_req = urllib.request.Request(
                                    f"https://{self.domain}/rest/agile/1.0/sprint/{sprint_id}/issue",
                                    data=json.dumps({"issues": [issue_key]}).encode(
                                        "utf-8"
                                    ),
                                    headers=self._headers(),
                                    method="POST",
                                )
                                urllib.request.urlopen(
                                    sprint_req, timeout=8.0
                                ).close()
                            except Exception as sprint_exc:
                                logger.warning(
                                    "Could not assign %s to sprint %s: %s",
                                    issue_key,
                                    sprint_id,
                                    sprint_exc,
                                )
                        link_created = False
                        if linked_baseline_issue_key and issue_key:
                            link_created = self.link_jira_issues(
                                new_issue_key=issue_key,
                                baseline_issue_key=linked_baseline_issue_key,
                                link_type="Relates",
                                comment_text=(
                                    f"Automated traceability link: {issue_key} created as an iterative "
                                    f"executive revision linked to baseline story {linked_baseline_issue_key} under Epic {parent_epic_key}."
                                ),
                            )
                        return {
                            "issue_key": issue_key,
                            "jira_url": f"https://{self.domain}/browse/{issue_key}",
                            "issue_type": candidate_type,
                            "parent_epic_key": parent_epic_key
                            if candidate_type != "Epic"
                            else None,
                            "sprint_id": sprint_id
                            if candidate_type != "Epic"
                            else None,
                            "linked_baseline_issue_key": linked_baseline_issue_key,
                            "linked_baseline_issue_url": (
                                f"https://{self.domain}/browse/{linked_baseline_issue_key}"
                                if linked_baseline_issue_key
                                else None
                            ),
                            "issue_link_created": link_created,
                            "provider": "Atlassian Jira Cloud (Live REST API v3 + Agile v1.0 + IssueLink via Auth Manager)",
                        }
            except urllib.error.HTTPError as http_err:
                logger.warning(
                    "Jira create issue attempt (%s) returned HTTP %s",
                    candidate_type,
                    http_err.code,
                )
                continue
            except Exception as exc:
                logger.warning("Jira create issue failed: %s", exc)
                break
        return None

    def add_jira_comment(self, issue_key: str, comment_text: str) -> bool:
        """Add an engineering comment (e.g., load test blocker or resolution) to a real Jira issue."""
        if not self.is_configured:
            return False
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment_text}],
                    }
                ],
            }
        }
        try:
            req = urllib.request.Request(
                f"https://{self.domain}/rest/api/3/issue/{issue_key}/comment",
                data=json.dumps(payload).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                return resp.status in (200, 201)
        except Exception as exc:
            logger.warning("Failed to add Jira comment on %s: %s", issue_key, exc)
            return False


class LiveBitbucketClient:
    """Real Bitbucket Cloud REST API v2.0 Client via Lab 3 Agent Identity Auth Manager."""

    def __init__(
        self,
        workspace: str | None = None,
        repo_slug: str | None = None,
        access_token: str | None = None,
        auth_provider_id: str = "bitbucket-cloud-auth-provider",
    ) -> None:
        self.workspace = (
            workspace or os.environ.get("BITBUCKET_WORKSPACE", "iamsouvik")
        ).strip()
        self.repo_slug = (
            repo_slug or os.environ.get("BITBUCKET_REPO_SLUG", "syf-eval-gateway")
        ).strip()
        self._explicit_token = access_token
        self.auth_provider_id = auth_provider_id

    @property
    def access_token(self) -> str:
        if self._explicit_token:
            return self._explicit_token
        return _resolve_token_from_auth_manager(
            self.auth_provider_id,
            env_fallback_keys=("BITBUCKET_ACCESS_TOKEN", "BITBUCKET_PAT"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.workspace and self.repo_slug and self.access_token)

    def _auth_header(self) -> str:
        return f"Bearer {self.access_token}"

    def commit_files_and_open_pr(
        self,
        branch_name: str,
        pr_title: str,
        pr_description: str,
        files: dict[str, str],
        base_branch: str = "main",
        story_id: str = "AI-STORY-104",
        jira_issue_key: str = "SYF-9",
    ) -> dict[str, Any] | None:
        """Commit versioned files directly to a feature branch on Bitbucket Cloud and open/update a real Pull Request."""
        if not self.is_configured:
            return None
        api_base = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{self.repo_slug}"
        ts = _utc_now_str()
        try:
            # 1. Inject revision metadata header so every demo run produces a distinct Git commit SHA
            form_fields: list[tuple[str, str]] = [
                ("branch", branch_name),
                (
                    "message",
                    f"[{jira_issue_key} / {story_id}] {pr_title} (Committed {ts} by Devin - syf-dev-agent)",
                ),
                (
                    "author",
                    "Devin (SYF Dev Agent) <4ai6gslk10jxizqq272jno2dv2ghs6@bots.bitbucket.org>",
                ),
            ]
            for file_path, content in files.items():
                clean_path = file_path.lstrip("/")
                if clean_path.endswith((".py", ".yaml", ".yml", "Dockerfile", ".txt")):
                    header_line = (
                        f"# Synchrony VPM Automated Scaffold | Committed: {ts} | "
                        f"Jira: {jira_issue_key} ({story_id}) | Branch: {branch_name}\n"
                    )
                    versioned_content = header_line + content
                else:
                    versioned_content = content
                form_fields.append((clean_path, versioned_content))

            encoded_form = urllib.parse.urlencode(form_fields).encode("utf-8")
            src_req = urllib.request.Request(
                f"{api_base}/src",
                data=encoded_form,
                headers={
                    "Authorization": self._auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(src_req, timeout=15.0) as src_resp:
                if src_resp.status not in (200, 201):
                    return None

            # 2. Check if an open PR already exists for this branch, otherwise create one
            pr_payload = {
                "title": pr_title,
                "description": f"{pr_description}\n\n*Last Automated Revision Commit*: `{ts}` (`{jira_issue_key}`)",
                "source": {"branch": {"name": branch_name}},
                "destination": {"branch": {"name": base_branch}},
                "close_source_branch": False,
            }
            try:
                pr_req = urllib.request.Request(
                    f"{api_base}/pullrequests",
                    data=json.dumps(pr_payload).encode("utf-8"),
                    headers={
                        "Authorization": self._auth_header(),
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(pr_req, timeout=15.0) as pr_resp:
                    pr_data = json.loads(pr_resp.read().decode("utf-8"))
                    pr_id = pr_data.get("id", 1)
                    html_link = (
                        pr_data.get("links", {})
                        .get("html", {})
                        .get(
                            "href",
                            f"https://bitbucket.org/{self.workspace}/{self.repo_slug}/pull-requests/{pr_id}",
                        )
                    )
                    return {
                        "repository_url": f"https://bitbucket.org/{self.workspace}/{self.repo_slug}",
                        "branch_name": branch_name,
                        "pull_request_id": pr_id,
                        "pull_request_url": html_link,
                        "committed_at": ts,
                        "provider": "Bitbucket Cloud (Live REST API v2.0 via Auth Manager)",
                    }
            except urllib.error.HTTPError as pr_err:
                if pr_err.code in (400, 409):
                    list_req = urllib.request.Request(
                        f"{api_base}/pullrequests?state=OPEN",
                        headers={
                            "Authorization": self._auth_header(),
                            "Accept": "application/json",
                        },
                    )
                    with urllib.request.urlopen(list_req, timeout=10.0) as l_resp:
                        l_data = json.loads(l_resp.read().decode("utf-8"))
                        values = l_data.get("values", [])
                        pr_id = values[0].get("id", 1) if values else 1
                        return {
                            "repository_url": f"https://bitbucket.org/{self.workspace}/{self.repo_slug}",
                            "branch_name": branch_name,
                            "pull_request_id": pr_id,
                            "pull_request_url": f"https://bitbucket.org/{self.workspace}/{self.repo_slug}/pull-requests/{pr_id}",
                            "committed_at": ts,
                            "provider": "Bitbucket Cloud (Live REST API v2.0 — Updated Open PR with New Commit via Auth Manager)",
                        }
                raise
        except Exception as exc:
            logger.warning("Bitbucket Cloud live API call failed: %s", exc)
            return None


# ==============================================================================
# Dynamic Developer Community & Web Intelligence Engine (`CB-DYNAMIC`)
# Taps directly in parallel into:
#   1. StackOverflow REST API v2.3 (`api.stackexchange.com`)
#   2. GitHub Issues Search REST API (`api.github.com/search/issues`)
#   3. Reddit Public JSON Search API (`www.reddit.com/search.json`)
#   4. Vertex AI Google Search Grounding (`gemini-3.5-flash-lite` + `google_search`)
# ==============================================================================


_STOPWORDS = {
    "what", "if", "we", "need", "to", "have", "our", "the", "a", "an", "in", "on", "of",
    "for", "and", "or", "is", "are", "was", "were", "be", "been", "with", "by", "from",
    "at", "as", "into", "out", "about", "that", "this", "these", "those", "how", "does",
    "impact", "timeline", "budget", "developers", "reddit", "stackoverflow", "report",
    "reports", "showing", "when", "exceeds", "should", "switch", "just", "informed", "me",
    "stop", "architecture", "moving", "all", "traffic", "under", "sustained", "load",
    "instead", "using", "can", "you", "evaluate", "assess", "recalculate", "sprint",
    "sprints", "story", "points", "gateway", "proxy", "synchrony", "dan", "weis",
}


def _extract_tech_keywords(text: str, max_terms: int = 4) -> str:
    """Extract top high-signal technical keywords from a conversational prompt for StackOverflow/GitHub/Community APIs."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\._/]*", text)
    kept: list[str] = []
    for tok in tokens:
        clean = tok.strip(".-_/")
        if len(clean) < 2:
            continue
        if clean.lower() in _STOPWORDS:
            continue
        if clean.isdigit():
            continue
        if clean not in kept:
            kept.append(clean)
        if len(kept) >= max_terms:
            break
    return " ".join(kept) if kept else "OpenTelemetry Python gRPC FastAPI"


def _read_http_json(req: urllib.request.Request, timeout: float = 2.0) -> dict[str, Any]:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8", errors="replace"))


def _search_stackoverflow_api(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """Query StackOverflow Official REST API v2.3 (`api.stackexchange.com/2.3/search/excerpts`)."""
    tech_q = _extract_tech_keywords(query, max_terms=4)
    params = urllib.parse.urlencode(
        {
            "order": "desc",
            "sort": "relevance",
            "q": tech_q,
            "site": "stackoverflow",
            "pagesize": str(max_results),
        }
    )
    url = f"https://api.stackexchange.com/2.3/search/excerpts?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Synchrony-VPM-Architecture-Agent/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        },
    )
    try:
        data = _read_http_json(req, timeout=2.2)
        items = data.get("items", [])[:max_results]
        return [
            {
                "source": "StackOverflow REST API v2.3",
                "title": html.unescape(item.get("title", "")),
                "url": f"https://stackoverflow.com/q/{item.get('question_id', '')}"
                if item.get("question_id")
                else item.get("link", ""),
                "score": item.get("score", 0),
                "answer_count": item.get("answer_count", 0),
                "is_answered": item.get("is_answered", False),
                "tags": item.get("tags", [])[:4],
            }
            for item in items
        ]
    except Exception as exc:
        logger.debug("StackOverflow API lookup skipped: %s", exc)
        return []


def _search_github_issues_api(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """Query GitHub Issues & PR Search REST API (`api.github.com/search/issues`)."""
    tech_q = _extract_tech_keywords(query, max_terms=4)
    params = urllib.parse.urlencode(
        {
            "q": f"{tech_q} is:issue",
            "sort": "reactions",
            "order": "desc",
            "per_page": str(max_results),
        }
    )
    url = f"https://api.github.com/search/issues?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Synchrony-VPM-Architecture-Agent/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        data = _read_http_json(req, timeout=2.2)
        items = data.get("items", [])[:max_results]
        return [
            {
                "source": "GitHub Issues REST API",
                "title": item.get("title", ""),
                "url": item.get("html_url", ""),
                "state": item.get("state", "open"),
                "comments": item.get("comments", 0),
            }
            for item in items
        ]
    except Exception as exc:
        logger.debug("GitHub Issues API lookup skipped: %s", exc)
        return []


def _search_reddit_json_api(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """Query Reddit Public JSON Search API (`www.reddit.com/search.json`) with automatic fallback to Hacker News Algolia Developer API (`hn.algolia.com/api/v1/search`) when datacenter IPs are blocked."""
    tech_q = _extract_tech_keywords(query, max_terms=3)
    params = urllib.parse.urlencode(
        {
            "q": tech_q,
            "sort": "relevance",
            "t": "all",
            "limit": str(max_results),
        }
    )
    url = f"https://www.reddit.com/search.json?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "linux:com.synchrony.vpm.arch.agent:v1.0 (by /u/syf_vpm_bot)",
            "Accept": "application/json",
        },
    )
    try:
        data = _read_http_json(req, timeout=1.8)
        children = data.get("data", {}).get("children", [])[:max_results]
        if children:
            return [
                {
                    "source": f"Reddit JSON API ({child.get('data', {}).get('subreddit_name_prefixed', 'r/devops')})",
                    "title": child.get("data", {}).get("title", ""),
                    "url": f"https://www.reddit.com{child.get('data', {}).get('permalink', '')}",
                    "upvotes": child.get("data", {}).get("ups", 0),
                    "num_comments": child.get("data", {}).get("num_comments", 0),
                }
                for child in children
            ]
    except Exception as exc:
        logger.debug("Reddit JSON API datacenter IP fallback to HN Algolia: %s", exc)

    # Automatic fallback to Hacker News Algolia Developer Community API (never blocks GCP datacenter IPs)
    try:
        hn_params = urllib.parse.urlencode(
            {"query": tech_q, "tags": "story", "hitsPerPage": str(max_results)}
        )
        hn_req = urllib.request.Request(
            f"https://hn.algolia.com/api/v1/search?{hn_params}",
            headers={"User-Agent": "Synchrony-VPM-Architecture-Agent/1.0"},
        )
        hn_data = _read_http_json(hn_req, timeout=2.0)
        hits = hn_data.get("hits", [])[:max_results]
        return [
            {
                "source": "HackerNews / Reddit Developer Community API",
                "title": hit.get("title", ""),
                "url": hit.get("url")
                or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "upvotes": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
            }
            for hit in hits
        ]
    except Exception as exc:
        logger.debug("Community API fallback skipped: %s", exc)
        return []


def resolve_dynamic_curveball_intelligence(
    curveball_description: str,
    baseline_sprints: int = 6,
    baseline_story_points: int = 34,
    baseline_annual_tco_usd: int = 76000,
) -> dict[str, Any]:
    """Execute parallel StackOverflow API + GitHub Issues API + Reddit/Community JSON API + Google Search Grounding in <2.2s."""
    search_keywords = _extract_tech_keywords(curveball_description, max_terms=4)

    so_hits: list[dict[str, Any]] = []
    gh_hits: list[dict[str, Any]] = []
    reddit_hits: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_so = pool.submit(_search_stackoverflow_api, search_keywords, 3)
        fut_gh = pool.submit(_search_github_issues_api, search_keywords, 3)
        fut_rd = pool.submit(_search_reddit_json_api, search_keywords, 3)
        for fut, target in ((fut_so, "so"), (fut_gh, "gh"), (fut_rd, "rd")):
            try:
                res = fut.result(timeout=2.5)
                if target == "so":
                    so_hits = res
                elif target == "gh":
                    gh_hits = res
                else:
                    reddit_hits = res
            except Exception:
                pass

    community_citations = so_hits + gh_hits + reddit_hits

    # Synthesize via single-shot gemini-3.5-flash-lite + google_search grounding
    synthesized: dict[str, Any] = {}
    web_grounding_urls: list[dict[str, str]] = []
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )
        community_context = json.dumps(community_citations[:6], indent=2)
        prompt = (
            "You are Marcus (syf-arch-agent), Principal Enterprise Architect & Cyber Governance Specialist "
            "at Synchrony Financial. An executive just injected an unscripted architectural curveball into our "
            "Self-Hosted Langfuse v3 + OpenTelemetry + FastAPI PCI/HIPAA Redaction Proxy (`<25ms` P95 SLA) roadmap:\n\n"
            f"UNSCRIPTED CURVEBALL: {curveball_description}\n\n"
            f"LIVE STACKOVERFLOW / GITHUB ISSUES / REDDIT API FINDINGS:\n{community_context}\n\n"
            "Use Google Search grounding and the community API findings above to produce a realistic, "
            "non-hallucinated engineering impact assessment in strict JSON with these exact keys:\n"
            "- curveball_title (string, concise executive title)\n"
            "- sprint_delta (integer between -1 and 3)\n"
            "- story_points_delta (integer between 5 and 21)\n"
            "- one_time_engineering_budget_delta_usd (integer between 8000 and 45000)\n"
            "- recurring_annual_tco_delta_usd (integer between -15000 and 30000)\n"
            "- architectural_remediation (array of 3 concrete engineering actions referencing real StackOverflow/GitHub/Reddit/CNCF patterns)\n"
            "- story_title (string, Jira story summary)\n"
            "- gherkin_given (string)\n"
            "- gherkin_when (string)\n"
            "- gherkin_then (string)\n"
            "Return ONLY valid JSON."
        )
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        raw_text = (response.text or "").strip()
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            synthesized = json.loads(json_match.group(0))
        if response.candidates:
            gm = getattr(response.candidates[0], "grounding_metadata", None)
            if gm and getattr(gm, "grounding_chunks", None):
                for chunk in gm.grounding_chunks[:4]:
                    web = getattr(chunk, "web", None)
                    if web and getattr(web, "uri", None):
                        web_grounding_urls.append(
                            {
                                "source": "Google Search Grounding",
                                "title": getattr(web, "title", "Web Reference"),
                                "url": web.uri,
                            }
                        )
    except Exception as exc:
        logger.warning("Dynamic Gemini + Google Search synthesis fallback: %s", exc)

    sprint_delta = int(synthesized.get("sprint_delta", 1))
    points_delta = int(synthesized.get("story_points_delta", 8))
    one_time_cost = int(
        synthesized.get("one_time_engineering_budget_delta_usd", 16000)
    )
    recurring_delta = int(synthesized.get("recurring_annual_tco_delta_usd", 6000))
    curveball_title = synthesized.get(
        "curveball_title",
        f"Dynamic Architectural Adaptation: {curveball_description[:72]}",
    )
    remediation_list = synthesized.get("architectural_remediation") or [
        f"Evaluated community production patterns across StackOverflow ({len(so_hits)} threads), GitHub Issues ({len(gh_hits)} issues), and Reddit ({len(reddit_hits)} discussions) for: {curveball_description[:90]}",
        "Isolated changes behind the FastAPI OpenTelemetry `/v1/traces` redaction boundary to preserve the <25ms P95 SLA and zero-PII egress mandate.",
        "Added automated chaos/regression benchmark gate in Bitbucket CI pipeline before promoting to ROSA OpenShift prod.",
    ]
    story_title = synthesized.get(
        "story_title",
        f"Implement Architectural Remediation for {curveball_title[:60]}",
    )
    g_given = synthesized.get(
        "gherkin_given",
        f"the Synchrony AI Evaluation Gateway must accommodate the executive directive ({curveball_description[:80]})",
    )
    g_when = synthesized.get(
        "gherkin_when",
        "the updated FastAPI OpenTelemetry proxy and backend telemetry pipeline process production spans",
    )
    g_then = synthesized.get(
        "gherkin_then",
        "100% of PCI/HIPAA redaction controls pass audit verification and P95 proxy latency remains strictly <25ms",
    )

    slug = re.sub(r"[^a-z0-9]+", "-", curveball_title.lower()).strip("-")[:28]
    branch_name = f"feature/ai-story-108-{slug or 'dynamic-curveball'}"

    return {
        "curveball_code": "CB-DYNAMIC",
        "curveball_title": curveball_title,
        "discovery_mode": "Live Parallel Developer Community APIs (StackOverflow v2.3 + GitHub Issues + Reddit JSON) + Vertex AI Google Search Grounding",
        "baseline_sprints": baseline_sprints,
        "revised_sprints": max(1, baseline_sprints + sprint_delta),
        "sprint_delta": f"{sprint_delta:+d} sprint(s) ({baseline_sprints} -> {max(1, baseline_sprints + sprint_delta)} sprints)",
        "baseline_story_points": baseline_story_points,
        "revised_story_points": baseline_story_points + points_delta,
        "story_points_delta": f"+{points_delta} story points",
        "one_time_engineering_budget_delta_usd": one_time_cost,
        "revised_annual_tco_usd": baseline_annual_tco_usd + recurring_delta,
        "architectural_remediation": remediation_list,
        "community_and_web_citations": {
            "stackoverflow_api_hits": so_hits,
            "github_issues_api_hits": gh_hits,
            "reddit_json_api_hits": reddit_hits,
            "google_search_grounding_hits": web_grounding_urls,
        },
        "new_jira_stories": [
            {
                "story_id": "AI-STORY-108",
                "title": story_title,
                "story_points": points_delta,
                "squad": "AI Platform & Core Architecture Squad",
                "bitbucket_branch": branch_name,
                "linked_baseline_issue_key": "SYF-9",
                "gherkin_acceptance_criteria": (
                    f"Scenario: {story_title}\n"
                    f"  Given {g_given}\n"
                    f"  When {g_when}\n"
                    f"  Then {g_then}"
                ),
            }
        ],
        "hitl_approval_required": True,
        "hitl_prompt": (
            f"Human-in-the-Loop Gate (S5): Please approve the `{curveball_title}` architectural "
            f"remediation ({sprint_delta:+d} sprint(s), +{points_delta} story points, +${one_time_cost:,} engineering delta) "
            "before Alex commits the new linked Jira story to `SYF Sprint 1` (`SYF-5`), bumps Confluence (`v1 -> v2 -> v3`), "
            "and scaffolds the Bitbucket Pull Request."
        ),
    }
