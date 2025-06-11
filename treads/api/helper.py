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
- extract_text_response_from_tool_result: Gets text from tool call results
- extract_text_from_prompt_result: Gets text from prompt results with multiple formats
- extract_text_from_resource_result: Extracts text content from resource results
"""

import json
import logging
from typing import Any, Callable, Optional, Union

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

from treads.nanobot.client import NanobotClient

logger = logging.getLogger("treads.api.helper")


# Client Operations

async def with_nanobot_client(operation: Callable, *args, **kwargs) -> Any:
    """Execute an operation with a NanobotClient, handling connection and errors."""
    async with NanobotClient() as client:
        return await operation(client, *args, **kwargs)


async def handle_client_operation(
    operation_name: str,
    operation: Callable,
    success_key: Optional[str] = None,
    *args,
    **kwargs
) -> Any:
    """Generic handler for client operations with error handling."""
    try:
        result = await with_nanobot_client(operation, *args, **kwargs)
        if success_key:
            return {success_key: result}
        return result
    except Exception as e:
        logger.error(f"Error in {operation_name}: {e}")
        raise HTTPException(status_code=502, detail=str(e))


async def handle_client_list_operation(
    operation_name: str,
    method_name: str,
    success_key: str
) -> dict:
    """Generic handler for list operations with hasattr check."""
    async def list_operation(client):
        if hasattr(client, method_name):
            return await getattr(client, method_name)()
        else:
            return []
    
    return await handle_client_operation(
        operation_name,
        list_operation,
        success_key
    )


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


def extract_text_response_from_tool_result(result: Any) -> str:
    """Extract text response from tool call result."""
    if isinstance(result, list) and result:
        for item in result:
            item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
            item_text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
            if item_type == "text" and item_text:
                return item_text
    return "No response"


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


async def get_agent_view_snippet(agent_name: str, snippet_name: str, fallback_html: Optional[str] = None) -> str:
    """
    Get a view snippet for an agent, falling back to default if not found.
    
    Args:
        agent_name: Name of the agent
        snippet_name: Name of the snippet (e.g., 'chat_response')
        fallback_html: Default HTML to use if no snippet found
    
    Returns:
        HTML string for the snippet
    """
    uri = f"ui://{agent_name}/{snippet_name}"
    
    try:
        async with NanobotClient() as client:
            result = await client.read_resource(uri=uri)
        
        # Extract HTML from resource result
        html_content = extract_text_from_resource_result(result)
        if html_content:
            # Try to parse as JSON resource first
            try:
                parsed = json.loads(html_content)
                if isinstance(parsed, dict) and "content" in parsed:
                    return parsed["content"].get("text", html_content)
                return html_content
            except json.JSONDecodeError:
                # Plain HTML snippet
                return html_content
                
    except Exception as e:
        logger.debug(f"Agent snippet not found at {uri}: {e}")
    
    # Return fallback or default
    if fallback_html:
        return fallback_html
    
    # Default snippets
    defaults = {
        "chat_response": '<div class="chat-bubble chat-bubble-bot">{response}</div>',
        "error_response": '<div class="chat-bubble chat-bubble-bot text-red-500">Error: {error}</div>'
    }
    
    return defaults.get(snippet_name, '<div>{content}</div>')


def render_snippet_with_context(snippet_html: str, context: dict) -> str:
    """
    Simple template variable substitution for snippets.
    
    Args:
        snippet_html: HTML snippet with {variable} placeholders
        context: Dictionary of variables to substitute
    
    Returns:
        Rendered HTML string
    """
    rendered = snippet_html
    for key, value in context.items():
        rendered = rendered.replace(f"{{{key}}}", str(value))
    return rendered
