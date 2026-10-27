"""Latency-Optimized Vertex AI Memory Bank Manager for SYF Virtual Product Manager (Alex).

Avoids the compounding latency penalty of PreloadMemoryTool() (which fires before
every intra-turn LLM tool step) by using a Turn-1 session-cached bootstrap callback
combined with on-demand LoadMemoryTool() and asynchronous after_agent_callback commit.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.load_memory_tool import LoadMemoryTool

logger = logging.getLogger(__name__)

# Configurable via environment variable:
# - "session_cached" (default): Searches Memory Bank ONCE on Turn 1 of a session and caches in state
# - "on_demand_only": Zero automatic search; relies strictly on LoadMemoryTool()
# - "preload_every_turn": Searches on every turn (for latency benchmarking comparison)
MEMORY_STRATEGY = os.environ.get("MEMORY_STRATEGY", "session_cached")

DEFAULT_SYF_INSTITUTIONAL_MEMORY = (
    "Synchrony Financial (SYF) Institutional Guardrails & Memory:\n"
    "1. Regulatory Status: OCC-Regulated Category II Bank ($100B+ loan receivables, 70M+ accounts).\n"
    "2. Zero-PII Rule: Raw cardholder PII, PCI-DSS PAN, SSN, or account numbers MUST NEVER leave "
    "the SYF boundary; Cloud DLP / Model Armor redaction is mandatory before any LLM or eval call.\n"
    "3. Approved Cloud Topology: GCP Vertex AI (us-central1) for GenAI & Eval workloads; "
    "AWS RedHat OpenShift (ROSA) (us-east-1) for core banking microservices.\n"
    "4. Cross-Cloud Network Warning: AWS Direct Connect / Cloud Interconnect between AWS us-east-1 "
    "and GCP us-central1 adds 40-60ms RTT. Inline synchronous cross-cloud evaluation calls violate "
    "the 50ms latency budget; use async Pub/Sub + BigQuery telemetry sidecar instead.\n"
    "5. Preferred Eval Strategy: Hybrid (Arize Phoenix OSS self-hosted on ROSA/GKE + Vertex AI "
    "Rapid Eval SDK for managed LLM-as-a-Judge).\n"
)


async def before_agent_memory_bootstrap(callback_context: CallbackContext) -> None:
    """Turn-1 session-cached memory bootstrap.

    Executes only once per session (when `session_cached` is active) to hydrate
    `state["institutional_memory"]` without adding network latency to every tool loop step.
    """
    if MEMORY_STRATEGY == "on_demand_only":
        if "institutional_memory" not in callback_context.state:
            callback_context.state["institutional_memory"] = DEFAULT_SYF_INSTITUTIONAL_MEMORY
        return None

    if (
        MEMORY_STRATEGY == "session_cached"
        and callback_context.state.get("memory_bootstrapped")
    ):
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
    """Commits session history to Vertex AI Memory Bank after turn completion."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as exc:
        logger.debug("Memory Bank commit skipped or non-fatal warning: %s", exc)
    return None


def get_on_demand_memory_tool() -> LoadMemoryTool:
    """Returns ADK LoadMemoryTool for explicit on-demand cross-session recall."""
    return LoadMemoryTool()
