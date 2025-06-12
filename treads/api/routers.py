import logging
import json
from datetime import datetime

from fastapi import HTTPException, Body, Request, Query, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder

from sse_starlette.sse import EventSourceResponse
from treads.nanobot.client import NanobotClient
from treads.api.helper import (
    handle_client_operation,
    handle_client_list_operation,
    extract_arguments_from_body,
    prefers_json,
    create_error_response,
    create_success_response,
    extract_prompt_from_body,
    extract_text_response_from_tool_result,
    extract_text_from_prompt_result,
    extract_text_from_resource_result,
    render_agent_view,
)

logger = logging.getLogger("treads.api.routers")
logging.basicConfig(level=logging.INFO)

MCPRouter = APIRouter()
TreadRouter = APIRouter()

# MCPRouter endpoints
@MCPRouter.post("/api/resources")
async def get_resource(body: dict = Body(...)):
    logger.info(f"Received body: {body}")
    uri = body.get("uri")
    if not uri:
        raise HTTPException(status_code=400, detail="Missing 'uri'")
    
    async def read_operation(client):
        result = await client.read_resource(uri)
        logger.info(f"Fetched resource: {result}")
        return result
    
    result = await handle_client_operation("get_resource", read_operation)
    return JSONResponse(content=jsonable_encoder(result))


@MCPRouter.get("/api/resources")
async def list_resources():
    return await handle_client_list_operation("list_resources", "list_resources", "resources")


@MCPRouter.get("/api/resource-templates")
async def list_resource_templates_mcp():
    return await handle_client_list_operation("list_resource_templates", "list_resource_templates", "templates")


@MCPRouter.get("/api/tools")
async def list_tools():
    return await handle_client_list_operation("list_tools", "list_tools", "tools")


@MCPRouter.get("/api/prompts")
async def list_prompts():
    async def list_operation(client):
        prompts = await client.list_prompts()
        return [p for p in prompts]
    
    result = await handle_client_operation("list_prompts", list_operation, "prompts")
    return result


@MCPRouter.post("/api/prompts/{name}")
async def get_prompt(name: str, body: dict = Body(None)):
    arguments = extract_arguments_from_body(body)
    
    async def prompt_operation(client):
        result = await client.get_prompt(name, arguments=arguments)
        return result
    
    try:
        result = await handle_client_operation("get_prompt", prompt_operation)
        return {"result": result}
    except HTTPException as e:
        # Add more context to the error
        raise HTTPException(status_code=e.status_code, detail=f"{e.detail}: input: {arguments}")

# TreadRouter endpoints

# Helper function that can be called directly
async def _get_ui_resource_helper(uri: str):
    """
    Internal helper function to fetch UI resources and always return HTML.
    """
    logger.info(f"Fetching UI resource: {uri}")
    if not uri or not uri.startswith("ui://"):
        raise HTTPException(status_code=400, detail="Missing or invalid 'uri' (must start with 'ui://')")
    
    try:
        async with NanobotClient() as client:
            result = await client.read_resource(uri=uri)
        # result is a list of TextResourceContents-like objects
        logger.info(f"Fetched UI resource: {result}")
        
        html_string = None
        for item in result:
            text = getattr(item, "text", None)
            if not text:
                continue
            try:
                parsed = json.loads(text)
                logger.info(f"Parsed resource text: {parsed}")
                html_string = parsed.get("content", {}).get("text")
                if html_string:
                    break
            except Exception as e:
                logger.error(f"Error parsing resource text as JSON: {e}")
                continue
        
        if not html_string:
            raise HTTPException(status_code=404, detail="No htmlString found in resource contents")
        
        return HTMLResponse(content=html_string)
            
    except Exception as e:
        logger.error(f"Error fetching UI resource: {e}")
        raise HTTPException(status_code=502, detail=str(e))

# Direct callable function for internal use
async def get_ui_resource(body: dict):
    """
    Direct callable version for internal use (like from server.py).
    Always returns HTML content.
    """
    uri = body.get("uri")
    if not uri:
        raise HTTPException(status_code=400, detail="Missing 'uri' parameter")
    return await _get_ui_resource_helper(uri)

@TreadRouter.post("/api/resources/ui")
async def get_ui_resource_endpoint(request: Request, body: dict = Body(...)):
    """
    FastAPI endpoint for fetching UI resources.
    Only supports 'ui://' URIs and returns the htmlString from the resource content.
    Always returns HTML content.
    """
    uri = body.get("uri")
    if not uri:
        raise HTTPException(status_code=400, detail="Missing 'uri' parameter")
    return await _get_ui_resource_helper(uri)


@TreadRouter.get("/api/templates")
async def list_resource_templates_tread(request: Request):
    """
    Lists non-UI resource templates.
    Returns a JSON object with 'templates' key containing a list of templates or renders as HTML with a template.
    """
    prefer_json = prefers_json(request)
    
    try:
        # Get templates and filter out UI ones
        async def get_filtered_templates(client):
            if hasattr(client, "list_resource_templates"):
                templates = await client.list_resource_templates()
            else:
                templates = []
            
            # Remove UI templates if any are present
            filtered_templates = []
            for t in templates:
                if not hasattr(t, "uriTemplate") or not t.uriTemplate.startswith("ui://"):
                    filtered_templates.append(t)
            return filtered_templates
        
        templates = await handle_client_operation("list_resource_templates", get_filtered_templates)
        
        uri = f"ui://app/resource_templates"
        html = await _get_ui_resource_helper(uri)

        return create_success_response(
            {"templates": html.body if hasattr(html, 'body') else str(html)},
            prefer_json,
            html
        )

    except Exception as e:
        logger.error(f"Error listing resource templates: {e}")
        return create_error_response(str(e), prefer_json, templates=[])

@TreadRouter.post("/api/{agent}/invoke")
async def invoke_agent(request: Request, agent: str, body: dict = Body(...)):
    """
    Invokes an agent with a prompt and returns a customizable response.
    Uses agent-specific view snippets from ui://{agent}/chat_response if available.
    """
    logger.info(f"Invoking agent '{agent}' with prompt")
    
    # Extract prompt using helper function
    prompt = extract_prompt_from_body(body)
    prefer_json = prefers_json(request)
    
    try:
        async def chat_operation(client):
            result = await client.call_tool("app", {"prompt": prompt})
            return extract_text_response_from_tool_result(result)
        
        response = await handle_client_operation(f"invoke_{agent}", chat_operation)
        
        # Extract response_type from response if it's a dict, default to "chat_response"
        response_type = "chat_response"
        if isinstance(response, dict) and "response_type" in response:
            response_type = response["response_type"]
            # Remove response_type from the response data so it doesn't appear in the template
            response_data = {k: v for k, v in response.items() if k != "response_type"}
        else:
            response_data = response
        
        # Handle structured data vs text for template rendering
        if isinstance(response_data, (dict, list)):
            # For structured data, pass both the raw data and a formatted version
            response_formatted = json.dumps(response_data, indent=2)
            response_for_json = response_data
        else:
            # For text responses, use as-is
            response_formatted = str(response_data)
            response_for_json = response_data
        
        template_context = {
            "response": response_data,  # Raw structured data for template access
            "response_formatted": response_formatted,  # Pretty-printed version for display
            "agent": agent,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat(),
            "response_type": response_type  # Include response_type in context
        }
        
        # Render agent-specific view with context using dynamic response_type
        rendered_html = await render_agent_view(agent, response_type, template_context)
        
        html_response = HTMLResponse(rendered_html)
        
        return create_success_response(
            {"response": response_for_json, "prompt": prompt, "agent": agent},
            prefer_json,
            html_response
        )
        
    except Exception as e:
        logger.error(f"Agent '{agent}' invocation failed: {e}")
        
        # Render agent-specific error snippet
        error_rendered_html = await render_agent_view(agent, "error_response", {
            "error": str(e),
            "agent": agent,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        return create_error_response(
            str(e), 
            prefer_json, 
            error_rendered_html,
            prompt=prompt,
            agent=agent
        )


@TreadRouter.post("/api/prompts/{name}/messages")
async def get_rendered_prompt_messages(request: Request, name: str, body: dict = Body(...)):
    arguments = extract_arguments_from_body(body)
    prefer_json = prefers_json(request)
    
    try:
        async def prompt_operation(client):
            result = await client.get_prompt(name, arguments=arguments)
            return extract_text_from_prompt_result(result)
        
        extracted_text = await handle_client_operation("get_rendered_prompt_messages", prompt_operation)
        
        return create_success_response(
            {"content": extracted_text, "prompt_name": name, "arguments": arguments},
            prefer_json,
            HTMLResponse(extracted_text)
        )
            
    except Exception as e:
        logger.error(f"Prompt rendered messages fetch failed: {e}")
        return create_error_response(str(e), prefer_json, prompt_name=name, arguments=arguments)


@TreadRouter.post("/api/templates/messages")
async def get_resource_with_instructions(request: Request, body: dict = Body(...)):
    """
    Accepts a URI directly in the request body along with optional user instructions.
    Retrieves the resource using the URI and sends it to the chat agent for a response.
    """
    uri = body.get("uri")
    instructions = body.get("instructions", "")
    prefer_json = prefers_json(request)
    
    if not uri:
        logger.error("Missing required 'uri' parameter")
        error_template = '<div class="chat-bubble chat-bubble-bot text-red-500">Missing required parameter: uri</div>'
        return create_error_response(
            "Missing required parameter: uri", 
            prefer_json, 
            error_template, 
            uri=None
        )
    
    try:
        logger.info(f"Fetching resource from URI: {uri}")
        
        async def resource_operation(client):
            result = await client.read_resource(uri=uri)
            logger.info(f"Resource result: {result}")
            
            # Extract text content from the resource
            extracted_content = extract_text_from_resource_result(result)
            
            if extracted_content:
                # Format the prompt for the chat agent
                prompt_text = f"Resource from {uri}:\n\n{extracted_content}"
                if instructions:
                    prompt_text += f"\n\nInstructions: {instructions}"
                return prompt_text
            else:
                # Return a generic message if we couldn't extract content
                return f"I'd like to know about the resource at {uri} {instructions}"
        
        prompt_text = await handle_client_operation("get_resource_with_instructions", resource_operation)
        
        return create_success_response(
            {"content": prompt_text, "uri": uri, "instructions": instructions},
            prefer_json,
            HTMLResponse(prompt_text)
        )
            
    except Exception as e:
        logger.error(f"Error processing resource request: {e}")
        error_template = '<div class="chat-bubble chat-bubble-bot text-red-500">Error retrieving resource: {error}</div>'
        return create_error_response(str(e), prefer_json, error_template, uri=uri, instructions=instructions)

@MCPRouter.post("/api/tools")
async def call_tool(
    request: Request,
    body: dict = Body(...),
    stream: int = Query(0)
):
    call = body.get("params")
    if call is None:
        # If not present, try to build params from flat form (HTMX form submission)
        # Accept prompt as the only argument for now
        prompt = body.get("prompt")
        if prompt is not None:
            call = {
                "name": "app",
                "arguments": {"prompt": prompt},
                "_meta": {}
            }
        else:
            raise HTTPException(status_code=400, detail="Missing 'params' or 'prompt' in request body")
    
    if not call:
        raise HTTPException(status_code=400, detail="Missing call parameters")
        
    tool_name = call.get("name")
    arguments = call.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="Missing 'name'")

    # Determine if streaming is requested
    stream_requested = (
        stream == 1
        or request.headers.get("x-stream", "0") == "1"
        or body.get("stream", False)
    )

    if stream_requested:
        async def event_generator():
            try:
                async with NanobotClient() as client:
                    result = await client.call_tool(tool_name, arguments)
                    yield {
                        "event": "complete",
                        "data": jsonable_encoder(result)
                    }
            except Exception as e:
                yield {
                    "event": "error",
                    "data": str(e)
                }

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    else:
        async def tool_operation(client):
                    return await client.call_tool(tool_name, arguments)
        
        result = await handle_client_operation("call_tool", tool_operation)
        return {"result": result}

# Export routers for use in main app
__all__ = ["MCPRouter", "TreadRouter", "get_ui_resource"]