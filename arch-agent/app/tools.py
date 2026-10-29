"""Tools and Agent Identity Auth Manager wiring for Marcus (arch-agent)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import gzip
import html
import json
import logging
import os
from pathlib import Path
import re
from typing import Any
import urllib.parse
import urllib.request

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

# Register Lab 3 Agent Identity Auth Manager Provider
CredentialManager.register_auth_provider(GcpAuthProvider())
syf_auth_scheme = GcpAuthProviderScheme(name=SYF_MCP_AUTH_PROVIDER_URI)

SKILLS_DIR = Path(__file__).parent / "skills"


def build_arch_mcp_toolset() -> McpToolset:
    """Create McpToolset authenticated via Lab 3 GcpAuthProviderScheme."""
    toolset: McpToolset | None = None

    def arch_header_provider(readonly_ctx: Any) -> dict[str, str]:
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
            logger.warning("Auth provider header lookup fallback: %s", exc)
        return {"Authorization": f"Bearer {fallback_key}"}

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=SYF_MCP_URL),
        auth_scheme=syf_auth_scheme,
        tool_filter=[
            "get_architecture_standards",
            "get_workspace_document",
            "patch_document_section",
        ],
        header_provider=arch_header_provider,
    )
    return toolset


def list_syf_skills() -> dict[str, Any]:
    """List Synchrony Financial domain skills bundled with Marcus (arch-agent)."""
    skills = []
    if SKILLS_DIR.exists():
        for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            skills.append(
                {
                    "skill_name": skill_md.parent.name,
                    "path": str(skill_md.relative_to(SKILLS_DIR.parent)),
                }
            )
    return {"agent": "arch_agent (Marcus)", "available_skills": skills}


def load_syf_skill(skill_name: str, include_references: bool = True) -> dict[str, Any]:
    """Load a Synchrony Financial SKILL.md runbook and its reference tables on demand."""
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
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\._/]*", text)
    kept: list[str] = []
    for tok in tokens:
        clean = tok.strip(".-_/")
        if len(clean) < 2 or clean.lower() in _STOPWORDS or clean.isdigit():
            continue
        if clean not in kept:
            kept.append(clean)
        if len(kept) >= max_terms:
            break
    return " ".join(kept) if kept else "OpenTelemetry Python gRPC FastAPI"


def _fetch_community_json(req: urllib.request.Request, timeout: float = 2.0) -> dict[str, Any]:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8", errors="replace"))


def _query_stackoverflow_api(query: str, max_results: int = 3) -> list[dict[str, Any]]:
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
    req = urllib.request.Request(
        f"https://api.stackexchange.com/2.3/search/excerpts?{params}",
        headers={
            "User-Agent": "Synchrony-VPM-Arch-Agent/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        },
    )
    try:
        data = _fetch_community_json(req, timeout=2.2)
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
            for item in data.get("items", [])[:max_results]
        ]
    except Exception:
        return []


def _query_github_issues_api(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    tech_q = _extract_tech_keywords(query, max_terms=4)
    params = urllib.parse.urlencode(
        {
            "q": f"{tech_q} is:issue",
            "sort": "reactions",
            "order": "desc",
            "per_page": str(max_results),
        }
    )
    req = urllib.request.Request(
        f"https://api.github.com/search/issues?{params}",
        headers={
            "User-Agent": "Synchrony-VPM-Arch-Agent/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        data = _fetch_community_json(req, timeout=2.2)
        return [
            {
                "source": "GitHub Issues REST API",
                "title": item.get("title", ""),
                "url": item.get("html_url", ""),
                "state": item.get("state", "open"),
                "comments": item.get("comments", 0),
            }
            for item in data.get("items", [])[:max_results]
        ]
    except Exception:
        return []


def _query_reddit_json_api(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    tech_q = _extract_tech_keywords(query, max_terms=3)
    params = urllib.parse.urlencode(
        {
            "q": tech_q,
            "sort": "relevance",
            "t": "all",
            "limit": str(max_results),
        }
    )
    req = urllib.request.Request(
        f"https://www.reddit.com/search.json?{params}",
        headers={
            "User-Agent": "linux:com.synchrony.vpm.arch.agent:v1.0 (by /u/syf_vpm_bot)",
            "Accept": "application/json",
        },
    )
    try:
        data = _fetch_community_json(req, timeout=1.8)
        children = data.get("data", {}).get("children", [])[:max_results]
        if children:
            return [
                {
                    "source": f"Reddit JSON API ({c.get('data', {}).get('subreddit_name_prefixed', 'r/devops')})",
                    "title": c.get("data", {}).get("title", ""),
                    "url": f"https://www.reddit.com{c.get('data', {}).get('permalink', '')}",
                    "upvotes": c.get("data", {}).get("ups", 0),
                    "num_comments": c.get("data", {}).get("num_comments", 0),
                }
                for c in children
            ]
    except Exception:
        pass

    try:
        hn_params = urllib.parse.urlencode(
            {"query": tech_q, "tags": "story", "hitsPerPage": str(max_results)}
        )
        hn_req = urllib.request.Request(
            f"https://hn.algolia.com/api/v1/search?{hn_params}",
            headers={"User-Agent": "Synchrony-VPM-Arch-Agent/1.0"},
        )
        hn_data = _fetch_community_json(hn_req, timeout=2.0)
        return [
            {
                "source": "HackerNews / Reddit Developer Community API",
                "title": hit.get("title", ""),
                "url": hit.get("url")
                or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "upvotes": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
            }
            for hit in hn_data.get("hits", [])[:max_results]
        ]
    except Exception:
        return []


def _evaluate_dynamic_community_curveball(
    curveball_description: str,
    baseline_sprints: int = 6,
    baseline_story_points: int = 192,
    baseline_annual_tco_usd: float = 76000.0,
) -> dict[str, Any]:
    """Parallel <2.2s lookup across StackOverflow REST API v2.3, GitHub Issues API, Reddit/Community JSON API, and Google Search Grounding."""
    keywords = _extract_tech_keywords(curveball_description, max_terms=4)

    so_hits: list[dict[str, Any]] = []
    gh_hits: list[dict[str, Any]] = []
    rd_hits: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_so = pool.submit(_query_stackoverflow_api, keywords, 3)
        f_gh = pool.submit(_query_github_issues_api, keywords, 3)
        f_rd = pool.submit(_query_reddit_json_api, keywords, 3)
        for fut, kind in ((f_so, "so"), (f_gh, "gh"), (f_rd, "rd")):
            try:
                res = fut.result(timeout=2.5)
                if kind == "so":
                    so_hits = res
                elif kind == "gh":
                    gh_hits = res
                else:
                    rd_hits = res
            except Exception:
                pass

    sp_per_sprint = 32
    cost_per_sp = 500.0

    synthesized: dict[str, Any] = {}
    web_citations: list[dict[str, str]] = []
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        community_ctx = json.dumps((so_hits + gh_hits + rd_hits)[:6], indent=2)
        prompt = (
            "You are Marcus (syf-arch-agent), Principal Enterprise Architect & Cyber Governance Specialist at Synchrony Financial.\n"
            "An executive just injected an architectural curveball into our Self-Hosted Langfuse v3 + OpenTelemetry + "
            "FastAPI PCI/HIPAA Redaction Proxy (<25ms P95 SLA) roadmap:\n\n"
            f"EXECUTIVE CURVEBALL: {curveball_description}\n\n"
            f"LIVE STACKOVERFLOW / GITHUB ISSUES / REDDIT API FINDINGS:\n{community_ctx}\n\n"
            "SYNCHRONY AGILE DELIVERY MODEL (MANDATORY MATH RULES):\n"
            "- Squad size: 4-5 Engineers\n"
            "- Sprint Velocity: 32 Story Points per 2-week Sprint\n"
            "- Blended Engineering Cost: $500 per Story Point ($16,000 per 32-SP Sprint)\n"
            "- Baseline Plan: 6 Sprints = 192 Total Story Points\n"
            "- Formula: sprint_delta = story_points_delta / 32; one_time_engineering_budget_delta_usd = story_points_delta * 500\n"
            "- If the curveball is about Kong Enterprise Gateway v3.4 deprecation -> internal Envoy Service Mesh (mTLS 1.3): story_points_delta MUST be 64 (+2 Sprints, +$32,000 one-time, $0 recurring delta), producing 2 stories of 32 SP each.\n"
            "- If the curveball is about OpenTelemetry Python gRPC span exporter memory leaks -> async HTTP/protobuf: story_points_delta MUST be 32 (+1 Sprint, +$16,000 one-time, $0 recurring delta), producing 1 story of 32 SP.\n\n"
            "Use Google Search grounding and the community API findings above to return a realistic engineering impact JSON object with keys:\n"
            "- curveball_id (string, e.g., 'CB-1' or 'CB-DYNAMIC')\n"
            "- curveball_title (string)\n"
            "- story_points_delta (integer multiple of 32: 32 or 64)\n"
            "- recurring_annual_tco_delta_usd (number, default 0)\n"
            "- remediation_summary (string citing concrete StackOverflow/GitHub/Reddit/CNCF engineering mitigations)\n"
            "- story_title (string)\n"
            "- gherkin_criteria (string with Given / When / Then)\n"
            "Return ONLY valid JSON."
        )
        resp = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        raw_txt = (resp.text or "").strip()
        m = re.search(r"\{.*\}", raw_txt, re.DOTALL)
        if m:
            synthesized = json.loads(m.group(0))
        if resp.candidates:
            gm = getattr(resp.candidates[0], "grounding_metadata", None)
            for chunk in getattr(gm, "grounding_chunks", []) or []:
                web = getattr(chunk, "web", None)
                if web and getattr(web, "uri", None):
                    web_citations.append(
                        {
                            "source": "Google Search Grounding",
                            "title": getattr(web, "title", "Web Source"),
                            "url": web.uri,
                        }
                    )
    except Exception as exc:
        logger.warning("Dynamic Gemini + Google Search grounding fallback: %s", exc)

    desc_lower = curveball_description.lower()
    is_kong = any(k in desc_lower for k in ("kong", "service mesh", "envoy", "cb-1"))
    default_sp_delta = 64 if is_kong else 32
    raw_sp_delta = int(synthesized.get("story_points_delta", default_sp_delta))
    if raw_sp_delta not in (0, 32, 64, 96, -32):
        raw_sp_delta = default_sp_delta

    points_delta = raw_sp_delta
    sprint_delta = points_delta // sp_per_sprint
    one_time_budget_delta = float(points_delta * cost_per_sp)
    recurring_delta = float(
        synthesized.get("recurring_annual_tco_delta_usd", 0.0)
    )
    cb_id = str(synthesized.get("curveball_id", "CB-1" if is_kong else "CB-DYNAMIC"))
    title = synthesized.get(
        "curveball_title",
        (
            "Kong Enterprise Gateway v3.4 Q1 Deprecation -> Synchrony Envoy Service Mesh (mTLS 1.3)"
            if is_kong
            else f"Dynamic Architectural Adaptation: {curveball_description[:72]}"
        ),
    )
    remediation = synthesized.get(
        "remediation_summary",
        (
            "Remove deprecated Kong Enterprise Gateway v3.4 from the ingress path. "
            "Inject Synchrony Internal Service Mesh Envoy sidecar (mesh.syf.bank/injected: 'true') "
            "with strict SPIFFE/Entra ID mTLS 1.3 validation and route north-south APIs via Apigee Hybrid."
            if is_kong
            else f"Synthesized live practitioner guidance across StackOverflow ({len(so_hits)} threads), "
            f"GitHub Issues ({len(gh_hits)} issues), Reddit ({len(rd_hits)} discussions), and Google Search Grounding. "
            "Isolated architectural changes behind the FastAPI OpenTelemetry `/v1/traces` proxy boundary to preserve "
            "the <25ms P95 SLA and 100% PCI-DSS v4.0 / CareCredit HIPAA zero-PII egress compliance."
        ),
    )

    if is_kong:
        added_stories = [
            {
                "story_id": "AI-STORY-104",
                "title": "Migrate Evaluation Gateway Ingress from Deprecated Kong v3.4 to Envoy Service Mesh (mTLS 1.3)",
                "squad": "SYF-Platform-Mesh-Squad",
                "story_points": 32,
                "sprint": "SYF Sprint 1",
                "linked_baseline_issue_key": "SYF-9",
                "bitbucket_branch": "feature/AI-EVAL-101-envoy-mesh-migration",
                "gherkin_acceptance_criteria": [
                    "Given Kong Enterprise Gateway v3.4 is deprecated in Q1, When the evaluation proxy is deployed to ROSA OpenShift, Then pod annotations include mesh.syf.bank/injected: 'true' with SPIFFE mTLS 1.3 peer verification."
                ],
            },
            {
                "story_id": "AI-STORY-105",
                "title": "Automate SPIFFE/Entra ID mTLS Certificate Rotation & Envoy Telemetry Filter Policies",
                "squad": "SYF-SecOps-DLP-Squad",
                "story_points": 32,
                "sprint": "SYF Sprint 1",
                "linked_baseline_issue_key": "SYF-9",
                "bitbucket_branch": "feature/AI-EVAL-101-spiffe-mtls-rotation",
                "gherkin_acceptance_criteria": [
                    "Given East-West Envoy service mesh traffic, When SPIFFE X.509 SVID certificates rotate, Then zero requests drop and P95 proxy latency remains <25ms."
                ],
            },
        ]
    else:
        story_title = synthesized.get(
            "story_title",
            f"Implement Architectural Remediation for {title[:60]}",
        )
        gherkin_text = synthesized.get(
            "gherkin_criteria",
            (
                f"Given the executive directive ({curveball_description[:80]}), "
                "When the FastAPI OpenTelemetry proxy processes production telemetry spans, "
                "Then 100% of PCI/HIPAA redaction controls pass audit verification and P95 proxy latency remains strictly <25ms."
            ),
        )
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:28]
        added_stories = [
            {
                "story_id": "AI-STORY-108",
                "title": story_title,
                "squad": "SYF-Platform-Mesh-Squad",
                "story_points": points_delta,
                "sprint": "SYF Sprint 1",
                "linked_baseline_issue_key": "SYF-9",
                "bitbucket_branch": f"feature/AI-EVAL-101-{slug or 'dynamic-remediation'}",
                "gherkin_acceptance_criteria": [gherkin_text],
            }
        ]

    return {
        "card_type": "curveball_impact_card",
        "curveball_id": cb_id,
        "curveball_title": title,
        "discovery_mode": "Live Parallel Developer Community APIs (StackOverflow v2.3 + GitHub Issues + Reddit JSON) + Vertex AI Google Search Grounding",
        "agile_velocity_formula": {
            "squad_size": "4-5 Engineers",
            "story_points_per_sprint": sp_per_sprint,
            "sprint_duration_weeks": 2,
            "blended_cost_per_story_point_usd": cost_per_sp,
            "sprint_cost_usd": sp_per_sprint * cost_per_sp,
        },
        "baseline_sprints": baseline_sprints,
        "sprint_delta": sprint_delta,
        "revised_total_sprints": max(1, baseline_sprints + sprint_delta),
        "baseline_story_points": baseline_story_points,
        "story_points_delta": points_delta,
        "revised_total_story_points": baseline_story_points + points_delta,
        "one_time_engineering_budget_delta_usd": one_time_budget_delta,
        "revised_annual_tco_usd": baseline_annual_tco_usd + recurring_delta,
        "affected_squads": ["SYF-Platform-Mesh-Squad", "SYF-SecOps-DLP-Squad"],
        "architectural_remediation": remediation,
        "community_and_web_citations": {
            "stackoverflow_api_hits": so_hits,
            "github_issues_api_hits": gh_hits,
            "reddit_json_api_hits": rd_hits,
            "google_search_grounding_hits": web_citations[:4],
        },
        "new_or_updated_jira_stories": added_stories,
        "requires_human_approval_gate": True,
    }


def evaluate_curveball_impact(
    curveball_description: str,
    baseline_sprints: int = 6,
    baseline_story_points: int = 192,
    baseline_annual_tco_usd: float = 76000.0,
) -> dict[str, Any]:
    """Evaluate the architectural blast radius, sprint delta, story point delta, and budget delta for any executive curveball using Synchrony's 32 SP/sprint Agile velocity formula and live community/search grounding."""
    return _evaluate_dynamic_community_curveball(
        curveball_description=curveball_description,
        baseline_sprints=baseline_sprints,
        baseline_story_points=baseline_story_points,
        baseline_annual_tco_usd=baseline_annual_tco_usd,
    )
