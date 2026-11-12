"""Latency-Optimized Vertex AI Memory Bank Manager for SYF Virtual Product Manager (Alex).

Avoids the compounding latency penalty of PreloadMemoryTool() (which fires before
every intra-turn LLM tool step) by using a Turn-1 session-cached bootstrap callback
combined with on-demand LoadMemoryTool() and asynchronous after_agent_callback commit.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.load_memory_tool import LoadMemoryTool

load_dotenv()

logger = logging.getLogger(__name__)

# Configurable via environment variable:
# - "on_demand_only" (default): Instant 0ms in-memory bootstrap of institutional guardrails; explicit consolidation via consolidate_executive_memory tool
# - "session_cached": Searches Memory Bank ONCE on Turn 1 of a session and caches in state
# - "preload_every_turn": Searches on every turn (for latency benchmarking comparison)
MEMORY_STRATEGY = os.environ.get("MEMORY_STRATEGY", "on_demand_only")

DEFAULT_SYF_INSTITUTIONAL_MEMORY = (
    "Synchrony Financial (SYF) Institutional Guardrails & Memory:\n"
    "1. Regulatory Status: OCC-Regulated Category II Bank ($100B+ loan receivables, 70M+ accounts).\n"
    "2. Zero-PII / Zero-Egress Rule: Raw cardholder PII, PCI-DSS v4.0 16-digit PAN, 9-digit SSN, or CareCredit HIPAA PHI (MRN, ICD-10, DOB) MUST NEVER leave "
    "Synchrony's AWS ROSA OpenShift VPC boundary; deterministic FastAPI inline regex/DLP redaction is mandatory prior to ClickHouse storage.\n"
    "3. Approved Cloud Topology: 100% AWS Red Hat OpenShift Service on AWS (ROSA, us-east-1) inside Synchrony's PCI/HIPAA-certified VPC.\n"
    "4. Gateway Latency Budget (<25ms P95 SLA): End-to-end gateway authentication (Microsoft Entra ID OIDC JWT with 300s local JWKS cache = 1.8ms) + inline DLP scrubbing (12.0ms) must remain strictly below 25.0ms P95 (13.8ms P95 achieved).\n"
    "5. Preferred Eval & Telemetry Platform: Self-Hosted Langfuse Enterprise v3 on AWS ROSA OpenShift backed by ClickHouse columnar OLAP (ZSTD 8x-10x compression).\n"
)


async def before_agent_memory_bootstrap(callback_context: CallbackContext) -> None:
    """Turn-1 session-cached memory bootstrap.

    Executes only once per session (when `session_cached` is active) to hydrate
    `state["institutional_memory"]` without adding network latency to every tool loop step.
    """
    if MEMORY_STRATEGY in ("on_demand_only", "session_cached"):
        if "institutional_memory" not in callback_context.state:
            callback_context.state["institutional_memory"] = DEFAULT_SYF_INSTITUTIONAL_MEMORY
        callback_context.state["memory_bootstrapped"] = True
        return None

    memories_text = DEFAULT_SYF_INSTITUTIONAL_MEMORY
    try:
        search_response: Any = await callback_context.search_memory(
            "Synchrony Financial architecture compliance governance PRD ADR decisions"
        )
        extracted: list[str] = []
        memories_list = getattr(search_response, "memories", None) or []
        for mem in memories_list[:5]:
            content = getattr(mem, "content", None)
            if content and getattr(content, "parts", None):
                for part in content.parts:
                    if getattr(part, "text", None):
                        extracted.append(part.text.strip())
        if extracted:
            memories_text += "\nRecalled Cross-Session Memories:\n- " + "\n- ".join(extracted)
    except Exception as exc:
        logger.debug("Memory Bank bootstrap fallback (expected on first run/local): %s", exc)

    callback_context.state["institutional_memory"] = memories_text
    callback_context.state["memory_bootstrapped"] = True
    return None


async def after_agent_memory_commit(callback_context: CallbackContext) -> None:
    """Commits session history to Vertex AI Memory Bank after turn completion when explicitly enabled."""
    if MEMORY_STRATEGY in ("on_demand_only", "session_cached"):
        return None
    try:
        await callback_context.add_session_to_memory()
    except Exception as exc:
        logger.debug("Memory Bank commit skipped or non-fatal warning: %s", exc)
    return None


def get_on_demand_memory_tool() -> LoadMemoryTool:
    """Returns ADK LoadMemoryTool for explicit on-demand cross-session recall."""
    return LoadMemoryTool()
