import json
import logging
import os
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from typing import Any

logger = logging.getLogger(__name__)

def get_a2ui_version() -> str:
    return os.environ.get("A2UI_VERSION", "v0.9")

def _wrap_a2ui_part(a2ui_message: dict) -> types.Part:
    """Wrap a single A2UI message for rendering in adk web / A2A."""
    from google.adk.a2a import _compat

    if getattr(_compat, "IS_A2A_V1", False):
        datapart_json = json.dumps(a2ui_message)
        blob_data = (
            b"<a2a_datapart_json>"
            + datapart_json.encode("utf-8")
            + b"</a2a_datapart_json>"
        )
        return types.Part(
            inline_data=types.Blob(
                data=blob_data,
                mime_type="text/plain",
            ),
            part_metadata={"mimeType": "application/json+a2ui"},
        )

    datapart_json = json.dumps({
        "kind": "data",
        "metadata": {"mimeType": "application/json+a2ui"},
        "data": a2ui_message,
    })
    blob_data = (
        b"<a2a_datapart_json>"
        + datapart_json.encode("utf-8")
        + b"</a2a_datapart_json>"
    )
    return types.Part(
        inline_data=types.Blob(
            data=blob_data,
            mime_type="text/plain",
        )
    )

def careconnect_a2ui_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Convert a2ui JSON payload inside the text response to rendered components."""
    if not llm_response.content or not llm_response.content.parts:
        return None
        
    new_parts = []
    has_a2ui = False
    
    for part in llm_response.content.parts:
        if not part.text:
            new_parts.append(part)
            continue
            
        text = part.text
        if "---a2ui_JSON---" in text:
            parts_split = text.split("---a2ui_JSON---", 1)
            conversational_text = parts_split[0].strip()
            json_text = parts_split[1].strip()
            
            # Clean JSON string (strip markdown code blocks if any)
            json_text = json_text.lstrip("```json").rstrip("```").strip()
            
            # Keep the conversational text part
            if conversational_text:
                new_parts.append(types.Part(text=conversational_text))
                
            try:
                # Parse JSON payload
                a2ui_data = json.loads(json_text)
                has_a2ui = True
                
                # Check if it's an object with "messages" or "a2ui_messages"
                if isinstance(a2ui_data, dict):
                    if "messages" in a2ui_data:
                        messages = a2ui_data["messages"]
                    elif "a2ui_messages" in a2ui_data:
                        messages = a2ui_data["a2ui_messages"]
                    else:
                        messages = [a2ui_data]
                elif isinstance(a2ui_data, list):
                    messages = a2ui_data
                else:
                    messages = [a2ui_data]
                    
                for msg in messages:
                    new_parts.append(_wrap_a2ui_part(msg))
                    
            except Exception as e:
                logging.error(f"Error parsing A2UI JSON in callback: {e}")
                # Fallback: append original text
                new_parts.append(part)
        else:
            new_parts.append(part)
            
    if has_a2ui:
        logging.info("A2UI callback successfully wrapped A2UI parts.")
        return LlmResponse(
            content=types.Content(role="model", parts=new_parts),
            custom_metadata={"a2a:response": "true"},
        )
        
    return None

def validate_a2ui(parsed_json: Any, version: str = "v0.9"):
    """Validates the parsed A2UI payload against the schema."""
    dir_path = os.path.dirname(__file__)
    
    if version in ("v0.9", "0.9"):
        try:
            # Load v0.9 schema files
            with open(os.path.join(dir_path, 'common_types_v0_9.json'), 'r') as f:
                common_types = json.load(f)
            with open(os.path.join(dir_path, 'composite_catalog_v0_9.json'), 'r') as f:
                catalog_schema = json.load(f)
            with open(os.path.join(dir_path, 'server_to_client_v0_9.json'), 'r') as f:
                s2c_schema = json.load(f)
                
            try:
                from a2ui.schema.catalog import A2uiCatalog
                from a2ui.schema.validator import A2uiValidator
            except (ImportError, ModuleNotFoundError):
                from a2ui.core.schema.catalog import A2uiCatalog
                from a2ui.core.schema.validator import A2uiValidator
            
            catalog = A2uiCatalog(
                version="0.9",
                name="gemini_enterprise_composite_catalog",
                catalog_schema=catalog_schema,
                common_types_schema=common_types,
                s2c_schema=s2c_schema
            )
            validator = A2uiValidator(catalog)
            
            payload_to_validate = parsed_json
            if isinstance(parsed_json, dict) and "messages" in parsed_json:
                payload_to_validate = parsed_json["messages"]
                
            validator.validate(payload_to_validate)
        except (ImportError, ModuleNotFoundError):
            from jsonschema import Draft202012Validator
            from referencing import Registry, Resource

            registry = Registry().with_resources([
                (common_types["$id"], Resource.from_contents(common_types)),
                (catalog_schema["$id"], Resource.from_contents(catalog_schema)),
                (s2c_schema["$id"], Resource.from_contents(s2c_schema)),
                ("catalog.json", Resource.from_contents(catalog_schema)),
                (
                    "https://a2ui.org/specification/v0_9/catalog.json",
                    Resource.from_contents(catalog_schema),
                ),
            ])
            s2c_validator = Draft202012Validator(s2c_schema, registry=registry)
            payload_to_validate = parsed_json
            if isinstance(parsed_json, dict) and "messages" in parsed_json:
                payload_to_validate = parsed_json["messages"]
            if not isinstance(payload_to_validate, list):
                payload_to_validate = [payload_to_validate]
            for env in payload_to_validate:
                s2c_validator.validate(env)
                if "updateComponents" in env:
                    for c in env["updateComponents"].get("components", []):
                        ctype = c["component"]
                        comp_schema = {
                            "$schema": "https://json-schema.org/draft/2020-12/schema",
                            "$ref": f"{catalog_schema['$id']}#/components/{ctype}",
                        }
                        Draft202012Validator(comp_schema, registry=registry).validate(c)
    else:
        import jsonschema
        schema_path = os.path.join(dir_path, 'a2ui_schema.json')
        with open(schema_path, 'r') as f:
            single_message_schema = json.load(f)
        schema_object = {
            "anyOf": [
                single_message_schema,
                {
                    "type": "array",
                    "items": single_message_schema
                },
                {
                    "type": "object",
                    "properties": {
                        "a2ui_messages": {
                            "type": "array",
                            "items": single_message_schema
                        }
                    },
                    "required": ["a2ui_messages"]
                }
            ]
        }
        jsonschema.validate(instance=parsed_json, schema=schema_object)
