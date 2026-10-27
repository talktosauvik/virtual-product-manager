"""Live Atlassian Cloud (Jira v3 + Confluence v1/v2) and Bitbucket Cloud v2.0 / GitHub REST API Client.

Designed to work seamlessly with Lab 3 (APEX013) Agent Identity Auth Manager credentials
or Cloud Run environment variables so that every SDLC tool in syf-mcp-server operates
against real Jira Cloud, real Confluence Cloud, and real Bitbucket Cloud / GitHub.
"""

from __future__ import annotations

import base64
import html
import json
import logging
import os
import re
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("syf-live-sdlc")


def _markdown_to_confluence_storage(md_text: str) -> str:
    """Convert Markdown into clean Confluence Storage Format XHTML."""
    lines = md_text.splitlines()
    out: list[str] = []
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


class LiveAtlassianClient:
    """Real Jira Software Cloud (REST v3) + Confluence Cloud (REST v1) integration."""

    def __init__(
        self,
        domain: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
        jira_project_key: str | None = None,
        confluence_space_key: str | None = None,
    ) -> None:
        raw_domain = (
            domain
            or os.environ.get("ATLASSIAN_DOMAIN", "")
            or os.environ.get("JIRA_CLOUD_DOMAIN", "")
        ).strip()
        self.domain = (
            raw_domain.replace("https://", "").replace("http://", "").strip("/")
        )
        self.email = (
            email
            or os.environ.get("ATLASSIAN_EMAIL", "")
            or os.environ.get("JIRA_USER_EMAIL", "")
        ).strip()
        self.api_token = (
            api_token
            or os.environ.get("ATLASSIAN_API_TOKEN", "")
            or os.environ.get("JIRA_API_TOKEN", "")
        ).strip()
        self.jira_project_key = (
            jira_project_key or os.environ.get("JIRA_PROJECT_KEY", "AIPLAT")
        ).strip()
        self.confluence_space_key = (
            confluence_space_key or os.environ.get("CONFLUENCE_SPACE_KEY", "AIPLAT")
        ).strip()

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
    ) -> dict[str, Any] | None:
        """Create or update a real Confluence Cloud page and return its live URL and version."""
        if not self.is_configured:
            return None
        target_space = space_key or self.confluence_space_key
        storage_xhtml = _markdown_to_confluence_storage(markdown_content)

        try:
            # 1. Check if page with this title already exists in the space
            query = urllib.parse.urlencode(
                {
                    "spaceKey": target_space,
                    "title": title,
                    "expand": "version",
                }
            )
            search_url = f"https://{self.domain}/wiki/rest/api/content?{query}"
            req = urllib.request.Request(search_url, headers=self._headers(), method="GET")
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
                update_payload = {
                    "id": page_id,
                    "type": "page",
                    "title": title,
                    "space": {"key": target_space},
                    "body": {
                        "storage": {
                            "value": storage_xhtml,
                            "representation": "storage",
                        }
                    },
                    "version": {
                        "number": next_version,
                        "message": version_comment,
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
                    return {
                        "page_id": str(page_id),
                        "version": next_version,
                        "space_key": target_space,
                        "confluence_url": f"https://{self.domain}/wiki{webui}"
                        if webui
                        else f"https://{self.domain}/wiki/spaces/{target_space}/pages/{page_id}",
                        "provider": "Atlassian Confluence Cloud (Live REST API)",
                    }
            else:
                create_payload = {
                    "type": "page",
                    "title": title,
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
                        "version": 1,
                        "space_key": target_space,
                        "confluence_url": f"https://{self.domain}/wiki{webui}"
                        if webui
                        else f"https://{self.domain}/wiki/spaces/{target_space}/pages/{page_id}",
                        "provider": "Atlassian Confluence Cloud (Live REST API)",
                    }
        except Exception as exc:
            logger.warning("Confluence Cloud live API call failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Jira Cloud REST API v3 (Create Issue / Epic / Story + Comments)
    # ------------------------------------------------------------------
    def create_jira_issue(
        self,
        summary: str,
        description_lines: list[str],
        issue_type: str = "Task",
        project_key: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create a real Jira Cloud issue (Epic, Story, or Task) using ADF formatting."""
        if not self.is_configured:
            return None
        proj = project_key or self.jira_project_key
        adf_content = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line}],
            }
            for line in description_lines
            if line.strip()
        ]
        # Try requested issue_type first, fall back to "Task" if project schema uses simplified types
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
                        return {
                            "issue_key": issue_key,
                            "jira_url": f"https://{self.domain}/browse/{issue_key}",
                            "issue_type": candidate_type,
                            "provider": "Atlassian Jira Cloud (Live REST API v3)",
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
    """Real Bitbucket Cloud REST API v2.0 Client for Branch, Multi-File Commit & Pull Request creation."""

    def __init__(
        self,
        workspace: str | None = None,
        repo_slug: str | None = None,
        access_token: str | None = None,
        username: str | None = None,
        app_password: str | None = None,
    ) -> None:
        self.workspace = (
            workspace or os.environ.get("BITBUCKET_WORKSPACE", "")
        ).strip()
        self.repo_slug = (
            repo_slug or os.environ.get("BITBUCKET_REPO_SLUG", "syf-eval-gateway")
        ).strip()
        self.access_token = (
            access_token or os.environ.get("BITBUCKET_ACCESS_TOKEN", "")
        ).strip()
        self.username = (
            username or os.environ.get("BITBUCKET_USERNAME", "")
        ).strip()
        self.app_password = (
            app_password or os.environ.get("BITBUCKET_APP_PASSWORD", "")
        ).strip()

    @property
    def is_configured(self) -> bool:
        return bool(
            self.workspace
            and self.repo_slug
            and (self.access_token or (self.username and self.app_password))
        )

    def _auth_header(self) -> str:
        if self.access_token:
            return f"Bearer {self.access_token}"
        creds = base64.b64encode(
            f"{self.username}:{self.app_password}".encode("utf-8")
        ).decode("utf-8")
        return f"Basic {creds}"

    def commit_files_and_open_pr(
        self,
        branch_name: str,
        pr_title: str,
        pr_description: str,
        files: dict[str, str],
        base_branch: str = "main",
    ) -> dict[str, Any] | None:
        """Commit scaffolded files directly to a feature branch on Bitbucket Cloud and open a real Pull Request."""
        if not self.is_configured:
            return None
        api_base = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{self.repo_slug}"
        try:
            # 1. Commit files directly to branch_name (Bitbucket /src endpoint creates branch if parents=main)
            form_fields: list[tuple[str, str]] = [
                ("branch", branch_name),
                ("message", f"{pr_title} (Scaffolded by Devin - syf-dev-agent)"),
            ]
            for file_path, content in files.items():
                clean_path = file_path.lstrip("/")
                form_fields.append((clean_path, content))

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

            # 2. Create Pull Request on Bitbucket Cloud
            pr_payload = {
                "title": pr_title,
                "description": pr_description,
                "source": {"branch": {"name": branch_name}},
                "destination": {"branch": {"name": base_branch}},
                "close_source_branch": False,
            }
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
                    "provider": "Bitbucket Cloud (Live REST API v2.0)",
                }
        except Exception as exc:
            logger.warning("Bitbucket Cloud live API call failed: %s", exc)
            return None
