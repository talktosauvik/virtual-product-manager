# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Attach A2A (Agent2Agent) + A2UI v0.9 endpoints to the FastAPI app.

func:`attach_a2a_routes` registers the dynamic agent-card endpoint (advertising
the A2UI v0.9 extension and Gemini Enterprise Composite Catalog) and the JSON-RPC
endpoint with an A2UI ExecuteInterceptor that attaches the 3-Card A2UI v0.9
Canvas surfaces (`createSurface`, `updateComponents`, `updateDataModel`) to the
final turn response.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv

load_dotenv()

from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import Event as A2AEvent
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import TaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentExtension,
    AgentInterface,
    Message,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a import _compat
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.executor.config import (
    A2aAgentExecutorConfig,
    ExecuteInterceptor,
)
from google.adk.a2a.executor.executor_context import ExecutorContext
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Struct

from app.app_utils.a2ui_utils import validate_a2ui
from app.ui_renderer import CATALOG_ID, select_a2ui_cards_for_turn

if TYPE_CHECKING:
    from fastapi import FastAPI
    from google.adk.agents import BaseAgent
    from google.adk.events.event import Event
    from google.adk.runners import Runner

logger = logging.getLogger(__name__)

# URI advertised on the agent card describing the executor extension shipped
# by ADK.
_ADK_AGENT_EXECUTOR_EXTENSION_URI = (
    "https://google.github.io/adk-docs/a2a/a2a-extension/"
)
_A2UI_EXTENSION_URI = "https://a2ui.org/a2a-extension/a2ui/v0.9"

# Per-task state tracking user query, stage, and final A2A parts for status completion
_TASK_A2UI_STATE: dict[str, dict[str, Any]] = {}


def _extract_query_and_stage_from_context(
    context: RequestContext,
) -> tuple[str, str | None]:
    """Extract user query text and optional A2UI action stage from incoming A2A message parts."""
    query_texts: list[str] = []
    stage: str | None = None

    message = context.message
    if not message or not message.parts:
        return "", None

    new_parts = []
    replaced_action_part = False

    for part in message.parts:
        part_dict: dict[str, Any] = {}
        try:
            if hasattr(part, "DESCRIPTOR"):
                part_dict = MessageToDict(part)
            elif hasattr(part, "model_dump"):
                part_dict = part.model_dump(exclude_none=True)
        except Exception as e:
            logger.warning("Failed to inspect incoming A2A part: %s", e)

        text_val = part_dict.get("text")
        if text_val:
            query_texts.append(text_val)
            low_t = text_val.lower()
            if "stage=curveball" in low_t:
                stage = "curveball"
            elif "stage=sdlc_approved" in low_t:
                stage = "sdlc_approved"
            elif "stage=sdlc_rejected" in low_t:
                stage = "sdlc_rejected"
            new_parts.append(part)
            continue

        data_val = part_dict.get("data")
        if isinstance(data_val, dict):
            # Support all A2UI v0.9 button event envelopes: action.event, userAction, event, action
            event_obj = (
                (data_val.get("action", {}) if isinstance(data_val.get("action"), dict) else {}).get("event")
                or data_val.get("userAction")
                or data_val.get("event")
                or data_val.get("action")
                or data_val
            )
            if isinstance(event_obj, dict):
                ev_name = str(event_obj.get("name", "")).lower()
                raw_ctx = event_obj.get("context", {})
                ctx: dict[str, Any] = {}
                if isinstance(raw_ctx, dict):
                    ctx = dict(raw_ctx)
                elif isinstance(raw_ctx, list):
                    for item in raw_ctx:
                        if isinstance(item, dict) and "key" in item:
                            val_obj = item.get("value")
                            if isinstance(val_obj, dict):
                                ctx[item["key"]] = (
                                    val_obj.get("stringValue")
                                    or val_obj.get(" literalString")
                                    or next(iter(val_obj.values()), "")
                                )
                            else:
                                ctx[item["key"]] = val_obj
                if ctx.get("stage"):
                    stage = str(ctx["stage"])
                elif "approve" in ev_name:
                    stage = "sdlc_approved"
                elif "reject" in ev_name:
                    stage = "sdlc_rejected"

                msg_from_btn = ctx.get("message")
                if not msg_from_btn and stage == "sdlc_approved":
                    msg_from_btn = (
                        "I approve the v1.1 architecture revisions and staged Sprint 1 backlog "
                        "(stage=sdlc_approved). Promote PRD-AI-EVAL-101 and ADR-001 to APPROVED on Confluence, "
                        "create all 8 Sprint 1 Jira stories (SYF-6 through SYF-13) assigned to Devin, and commit to Memory Bank."
                    )
                elif not msg_from_btn and stage == "sdlc_rejected":
                    msg_from_btn = (
                        "Reject / Keep in Draft (stage=sdlc_rejected): Keep PRD-AI-EVAL-101 v1.1 and the Sprint 1 "
                        "backlog in DRAFT status without committing to Jira or Confluence yet."
                    )
                if msg_from_btn:
                    query_texts.append(str(msg_from_btn))
                    new_parts.append(_compat.make_text_part(str(msg_from_btn)))
                    replaced_action_part = True
                    continue

        new_parts.append(part)

    if replaced_action_part and hasattr(message, "parts"):
        try:
            del message.parts[:]
            message.parts.extend(new_parts)
        except Exception as e:
            logger.warning("Could not rewrite action part into text part: %s", e)

    return "\n".join(query_texts).strip(), stage


async def _a2ui_before_agent(context: RequestContext) -> RequestContext:
    """Activate A2UI v0.9 extension and capture user query/stage before ADK runner executes."""
    try:
        if _A2UI_EXTENSION_URI in context.requested_extensions:
            _compat.add_activated_extension(context, _A2UI_EXTENSION_URI)
    except Exception as e:
        logger.debug("Extension activation skipped: %s", e)

    query, stage = _extract_query_and_stage_from_context(context)
    task_id = context.task_id or "default"
    _TASK_A2UI_STATE[task_id] = {
        "query": query,
        "stage": stage,
        "full_text": "",
        "executed_tools": [],
        "tool_outputs": {},
        "artifact_emitted": False,
        "final_parts": None,
    }
    return context


async def _a2ui_after_event(
    executor_context: ExecutorContext,
    a2a_event: A2AEvent,
    adk_event: Event,
) -> A2AEvent:
    """Track executed tools across ADK events and attach A2UI v0.9 DataParts to the final TaskArtifactUpdateEvent ONLY once."""
    task_id = getattr(a2a_event, "task_id", None) or "default"
    state = _TASK_A2UI_STATE.setdefault(
        task_id,
        {
            "query": "",
            "stage": None,
            "full_text": "",
            "executed_tools": [],
            "tool_outputs": {},
            "artifact_emitted": False,
            "final_parts": None,
            "cached_a2ui_messages": None,
        },
    )

    # Record any tool calls or tool responses emitted during this ADK step
    if adk_event and adk_event.content and adk_event.content.parts:
        for p in adk_event.content.parts:
            fc = getattr(p, "function_call", None)
            if fc and getattr(fc, "name", None):
                tname = str(fc.name)
                if tname not in state["executed_tools"]:
                    state["executed_tools"].append(tname)
            fr = getattr(p, "function_response", None)
            if fr and getattr(fr, "name", None):
                tname = str(fr.name)
                if tname not in state["executed_tools"]:
                    state["executed_tools"].append(tname)
                if getattr(fr, "response", None) and isinstance(fr.response, dict):
                    state["tool_outputs"][tname] = fr.response

    if not isinstance(a2a_event, TaskArtifactUpdateEvent):
        return a2a_event

    # Check if this ADK event is the final agent response turn
    is_final_turn = False
    try:
        is_final_turn = bool(adk_event and adk_event.is_final_response())
    except Exception:
        is_final_turn = bool(a2a_event.last_chunk)

    if not is_final_turn:
        return a2a_event

    # Prevent attaching A2UI cards more than once per turn
    if state.get("artifact_emitted"):
        return a2a_event

    # Extract conversational text from the final ADK event
    texts: list[str] = []
    if adk_event and adk_event.content and adk_event.content.parts:
        for p in adk_event.content.parts:
            if getattr(p, "text", None) and not getattr(p, "thought", False):
                texts.append(p.text)
    full_text = "\n".join(texts).strip()
    if full_text:
        state["full_text"] = full_text

    # Always mark artifact_emitted=True once TaskArtifactUpdateEvent is processed on the final turn
    # so _a2ui_after_agent never duplicates the text in TaskStatusUpdateEvent.
    state["artifact_emitted"] = True

    try:
        a2ui_messages = select_a2ui_cards_for_turn(
            query=state.get("query", ""),
            full_text=state.get("full_text", ""),
            stage=state.get("stage"),
            executed_tools=state.get("executed_tools", []),
            tool_outputs=state.get("tool_outputs", {}),
        )
        state["cached_a2ui_messages"] = a2ui_messages
        if a2ui_messages:
            validate_a2ui(a2ui_messages, version="v0.9")
            a2ui_parts = [
                _compat.make_data_part(
                    data=msg,
                    metadata={"mimeType": "application/json+a2ui"},
                )
                for msg in a2ui_messages
            ]
            a2a_event.artifact.parts.extend(a2ui_parts)
            logger.info(
                "Attached %d A2UI v0.9 DataParts to TaskArtifactUpdateEvent for task %s (tools=%s)",
                len(a2ui_parts),
                task_id,
                state.get("executed_tools"),
            )
        else:
            logger.info(
                "No A2UI v0.9 DataParts attached (pure native Markdown turn) on task %s (tools=%s)",
                task_id,
                state.get("executed_tools"),
            )
        state["final_parts"] = list(a2a_event.artifact.parts)
    except Exception as e:
        logger.error("Failed to attach A2UI v0.9 parts in after_event: %s", e)

    return a2a_event


async def _a2ui_after_agent(
    executor_context: ExecutorContext,
    final_event: TaskStatusUpdateEvent,
) -> TaskStatusUpdateEvent:
    """Only attach parts to TaskStatusUpdateEvent if TaskArtifactUpdateEvent did not already emit them (prevents duplicate turn rendering in Gemini Enterprise)."""
    task_id = final_event.task_id or "default"
    state = _TASK_A2UI_STATE.pop(task_id, None)
    if not state:
        return final_event

    # CRITICAL FIX: If TaskArtifactUpdateEvent already emitted the text + A2UI DataParts,
    # do NOT attach them again on TaskStatusUpdateEvent.status.message, or Gemini Enterprise renders the turn twice!
    if state.get("artifact_emitted"):
        return final_event

    try:
        full_text = state.get("full_text") or (
            "Synchrony GenAI Evaluation Gateway — Executive Summary."
        )
        a2ui_messages = state.get("cached_a2ui_messages")
        if a2ui_messages is None:
            a2ui_messages = select_a2ui_cards_for_turn(
                query=state.get("query", ""),
                full_text=full_text,
                stage=state.get("stage"),
                executed_tools=state.get("executed_tools", []),
                tool_outputs=state.get("tool_outputs", {}),
            )
        final_parts = [_compat.make_text_part(full_text)]
        if a2ui_messages:
            validate_a2ui(a2ui_messages, version="v0.9")
            final_parts.extend(
                _compat.make_data_part(
                    data=msg,
                    metadata={"mimeType": "application/json+a2ui"},
                )
                for msg in a2ui_messages
            )

        status_msg = Message(
            message_id=str(uuid.uuid4()),
            role=_compat.ROLE_AGENT,
            parts=final_parts,
        )
        new_status = _compat.make_task_status(
            final_event.status.state,
            message=status_msg,
        )
        if _compat.IS_A2A_V1:
            final_event.status.CopyFrom(new_status)
        else:
            final_event.status = new_status
    except Exception as e:
        logger.error("Failed to attach A2UI parts to terminal status event: %s", e)

    return final_event


def _add_v0_3_compat_interface(card: AgentCard) -> AgentCard:
    """Advertise a v0.3 JSON-RPC interface so the served card stays consumable by
    v0.3 A2A clients — notably registration with Gemini, whose validator
    still requires the 0.3 card shape (top-level ``url``/``protocolVersion``)."""
    if card.supported_interfaces and not any(
        i.protocol_binding == "JSONRPC" and i.protocol_version == "0.3"
        for i in card.supported_interfaces
    ):
        card.supported_interfaces.append(
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="0.3",
                url=card.supported_interfaces[0].url,
            )
        )
    return card


def _default_capabilities() -> AgentCapabilities:
    """Returns the A2A capabilities advertising both ADK Executor and A2UI v0.9 Canvas."""
    a2ui_ext = AgentExtension(
        uri=_A2UI_EXTENSION_URI,
        description="Ability to render A2UI v0.9 3-Card Vendor & CISO Canvas surfaces",
        required=False,
    )
    a2ui_params = {"supportedCatalogIds": [CATALOG_ID]}
    if _compat.IS_A2A_V1:
        a2ui_ext.params.CopyFrom(ParseDict(a2ui_params, Struct()))
    else:
        a2ui_ext.params = a2ui_params  # type: ignore[assignment]

    return AgentCapabilities(
        streaming=True,
        extensions=[
            AgentExtension(
                uri=_ADK_AGENT_EXECUTOR_EXTENSION_URI,
                description=("Ability to use the new agent executor implementation"),
            ),
            a2ui_ext,
        ],
    )


def _resolve_app_url(app_url: str | None) -> str:
    """Resolve the public base URL advertised inside the agent card."""
    if app_url:
        return app_url
    if env_url := os.getenv("APP_URL"):
        return env_url

    agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION", "us-central1")
    if agent_engine_id and project and location:
        return (
            f"https://{location}-aiplatform.googleapis.com/reasoningEngines/v1"
            f"/projects/{project}/locations/{location}"
            f"/reasoningEngines/{agent_engine_id}/api"
        )

    return "http://0.0.0.0:8000"


async def attach_a2a_routes(
    app: FastAPI,
    *,
    agent: BaseAgent,
    runner: Runner,
    task_store: TaskStore,
    rpc_path: str,
    capabilities: AgentCapabilities | None = None,
    agent_version: str | None = None,
    app_url: str | None = None,
) -> None:
    """Register A2A routes (JSON-RPC + agent-card endpoints) under ``rpc_path``."""
    resolved_app_url = _resolve_app_url(app_url)
    resolved_agent_version = agent_version or os.getenv("AGENT_VERSION", "0.1.0")
    resolved_capabilities = capabilities or _default_capabilities()

    agent_card = await AgentCardBuilder(
        agent=agent,
        capabilities=resolved_capabilities,
        rpc_url=f"{resolved_app_url}{rpc_path}",
        agent_version=resolved_agent_version,
    ).build()

    # Advertise a v0.3 JSON-RPC interface for registration with Gemini.
    agent_card = _add_v0_3_compat_interface(agent_card)

    executor_config = A2aAgentExecutorConfig(
        execute_interceptors=[
            ExecuteInterceptor(
                before_agent=_a2ui_before_agent,
                after_event=_a2ui_after_event,
                after_agent=_a2ui_after_agent,
            )
        ]
    )

    request_handler = DefaultRequestHandler(
        agent_executor=A2aAgentExecutor(
            runner=runner,
            config=executor_config,
            force_new_version=True,
        ),
        task_store=task_store,
        agent_card=agent_card,
    )

    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(
            agent_card,
            card_url=f"{rpc_path}{AGENT_CARD_WELL_KNOWN_PATH}",
        ),
        jsonrpc_routes=create_jsonrpc_routes(
            request_handler,
            rpc_url=rpc_path,
            enable_v0_3_compat=True,
        ),
    )
