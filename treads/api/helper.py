"""
Helper functions for API routers.

This module contains reusable helper functions to reduce code duplication across endpoints:

Client Operations:
- with_nanobot_client: Handles NanobotClient connection lifecycle
- handle_client_operation: Generic error handling wrapper for client operations
- handle_client_list_operation: Specialized handler for list operations with hasattr checks

Request/Response Helpers:
- extract_arguments_from_body: Extracts arguments from various request body formats
- prefers_json: Determines if client prefers JSON over HTML response
- create_error_response: Creates consistent error responses (JSON/HTML)
- create_success_response: Creates consistent success responses (JSON/HTML)

Data Extraction:
- extract_prompt_from_body: Extracts prompts from different request formats
- extract_text_response_from_tool_result: Gets response from tool call results (preserves structured data)
- extract_text_from_prompt_result: Gets text from prompt results with multiple formats
- extract_text_from_resource_result: Extracts text content from resource results
"""

import json
import logging
from typing import Any, Optional, Union

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from mcp.types import TextContent, ImageContent, EmbeddedResource

from treads.nanobot.client import NanobotClient
from treads.views.types import HTMLTextType, HTMLTemplate
from treads.views.jinja_env import get_jinja_env

logger = logging.getLogger("treads.api.helper")


# Request/Response Helpers

def extract_arguments_from_body(body: Optional[dict]) -> dict:
    """Extract arguments from request body in various formats."""
    arguments = {}
    if body:
        if "params" in body and isinstance(body["params"], dict) and "arguments" in body["params"]:
            arguments = body["params"]["arguments"]
        elif "arguments" in body:
            arguments = body["arguments"]
        else:
            arguments = body
    return arguments


def prefers_json(request: Request) -> bool:
    """Check if the request prefers JSON response based on Accept header."""
    accept_header = request.headers.get("Accept", "")
    return "application/json" in accept_header


def create_error_response(
    error: str,
    prefer_json: bool,
    html_template: Optional[str] = None,
    **extra_data
) -> Union[dict, HTMLResponse]:
    """Create consistent error responses for JSON or HTML."""
    if prefer_json:
        return {"success": False, "error": error, **extra_data}
    else:
        if html_template:
            return HTMLResponse(html_template.format(error=error))
        raise HTTPException(status_code=502, detail=error)


def create_success_response(
    data: Any,
    prefer_json: bool,
    html_response: Optional[HTMLResponse] = None,
    **extra_data
) -> Union[dict, HTMLResponse]:
    """Create consistent success responses for JSON or HTML."""
    if prefer_json:
        return {"success": True, **data, **extra_data}
    else:
        return html_response if html_response else data


# Data Extraction

def extract_prompt_from_body(body: dict) -> str:
    """Extract prompt from various request body formats."""
    if "prompt" in body:
        return body["prompt"]
    elif body.get("method") == "tools/call" and "params" in body:
        params = body["params"]
        if params.get("name") == "app" and "arguments" in params and "prompt" in params["arguments"]:
            return params["arguments"]["prompt"]
        else:
            raise HTTPException(status_code=400, detail="Invalid params for chat tool call")
    else:
        raise HTTPException(status_code=400, detail="Missing 'prompt' or invalid input format")


def extract_text_response_from_tool_result(result: Any) -> Any:
    """Extract response from tool call result, using MCP Pydantic types."""
    # Handle direct MCP Pydantic types
    if isinstance(result, TextContent):
        return result.text
    if isinstance(result, ImageContent):
        return result.data  # Use .data for image content
    if isinstance(result, EmbeddedResource):
        # Fallback: convert to string, as .data is not available
        return str(result)
    # Handle list of items (e.g., multiple responses)
    if isinstance(result, list) and result:
        # Return the content of the first recognized item
        for item in result:
            if isinstance(item, TextContent):
                return item.text
            if isinstance(item, ImageContent):
                return item.data
            if isinstance(item, EmbeddedResource):
                return str(item)
    # If result is already structured data, return as-is
    if isinstance(result, (dict, list)):
        return result
    # Fallback - try to convert to string
    return str(result) if result is not None else "No response"


def extract_text_from_prompt_result(result: Any) -> str:
    """Extract text content from prompt result with multiple message formats."""
    # If result has attribute 'messages' (not dict), extract from first message
    if hasattr(result, "messages") and isinstance(result.messages, list) and result.messages:
        first_msg = result.messages[0]
        # For objects like PromptMessage, get .content and then .text
        if hasattr(first_msg, "content") and hasattr(first_msg.content, "text"):
            return first_msg.content.text
        # Fallback for dict style
        elif isinstance(first_msg, dict):
            content = first_msg.get("content")
            if isinstance(content, dict):
                text = content.get("text")
                if text:
                    return text
    # If result is a dict with 'messages'
    elif isinstance(result, dict) and "messages" in result:
        msgs = result["messages"]
        if isinstance(msgs, list) and msgs:
            msg = msgs[0]
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if content:
                text = content.get("text") if isinstance(content, dict) else getattr(content, "text", None)
                if text:
                    return text
    # If already string, just return
    elif isinstance(result, str):
        return result
    
    # As a last resort, return stringified version
    return str(result)


def extract_text_from_resource_result(result: Any) -> Optional[str]:
    """Extract text content from a resource result."""
    if isinstance(result, list) and result:
        # Find the first text resource
        for item in result:
            if hasattr(item, "text"):
                content = getattr(item, "text")
                try:
                    # Try to parse as JSON
                    content_obj = json.loads(content)
                    if isinstance(content_obj, dict) and "text" in content_obj:
                        return content_obj["text"]
                    else:
                        return json.dumps(content_obj, indent=2)
                except json.JSONDecodeError:
                    # If not JSON, use the raw content as text
                    return content
                except Exception:
                    continue
    return None


async def fetch_and_render_ui_resource(uri: str, context: dict = {}) -> HTMLResponse:
    """
    Fetch a UI resource (HTMLTextType or HTMLTemplate) and render as HTML if needed.
    Handles stringified Pydantic types in .text attribute.
    """
    if context is None:
        context = {}
    if not uri or not uri.startswith("ui://"):
        raise HTTPException(status_code=400, detail="Missing or invalid 'uri' (must start with 'ui://')")
    try:
        async with NanobotClient() as client:
            result = await client.read_resource(uri=uri)
        for item in result:
            # 1. If item is a Pydantic HTMLTextType
            if isinstance(item, HTMLTextType):
                return HTMLResponse(content=item.html_string)
            # 2. If item is a Pydantic HTMLTemplate
            if isinstance(item, HTMLTemplate):
                template = get_jinja_env().env.from_string(item.template_content)
                return HTMLResponse(content=template.render(context))
            # 3. If item has a .text attribute, try to parse as JSON and instantiate
            text = getattr(item, "text", None)
            if text:
                try:
                    parsed = json.loads(text)
                    # Try HTMLTextType
                    if (
                        isinstance(parsed, dict)
                        and ("htmlString" in parsed or "html_string" in parsed)
                    ):
                        html_string = parsed.get("htmlString") or parsed.get("html_string")
                        return HTMLResponse(content=html_string)
                    # Try HTMLTemplate
                    if (
                        isinstance(parsed, dict)
                        and ("htmlTemplateString" in parsed or "template_content" in parsed)
                    ):
                        template_content = parsed.get("htmlTemplateString") or parsed.get("template_content")
                        if template_content:
                            context_schema = parsed.get("contextSchema") or parsed.get("context_schema", {})
                            template = get_jinja_env().env.from_string(template_content)
                            return HTMLResponse(content=template.render(context))
                except Exception as e:
                    logger.warning(f"Failed to parse .text as JSON for UI resource: {e}")
                    continue
        raise HTTPException(status_code=404, detail="No HTML content found in resource contents")
    except Exception as e:
        logger.error(f"Error fetching UI resource: {e}")
        raise HTTPException(status_code=502, detail=str(e))
