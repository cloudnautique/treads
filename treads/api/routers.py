import os
import logging
import json

from fastapi import HTTPException, Body, Request, Query, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder

from sse_starlette.sse import EventSourceResponse
from treads.nanobot.client import NanobotClient

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
    try:
        async with NanobotClient() as client:
            result = await client.read_resource(uri)
            logger.info(f"Fetched resource: {result}")
        return JSONResponse(content=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error fetching resource: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@MCPRouter.get("/api/resources")
async def list_resources():
    try:
        async with NanobotClient() as client:
            if hasattr(client, "list_resources"):
                resources = await client.list_resources()
            else:
                resources = []
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@MCPRouter.get("/api/resource-templates")
async def list_resource_templates():
    try:
        async with NanobotClient() as client:
            if hasattr(client, "list_resource_templates"):
                templates = await client.list_resource_templates()
            else:
                templates = []
        return {"templates": templates}
    except Exception as e:
        logger.error(f"Error listing resource templates: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@MCPRouter.get("/api/tools")
async def list_tools():
    try:
        async with NanobotClient() as client:
            if hasattr(client, "list_tools"):
                tools = await client.list_tools()
            else:
                tools = []
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=502, detail=str(e))


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
        try:
            async with NanobotClient() as client:
                result = await client.call_tool(tool_name, arguments)
            return {"result": result}
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            raise HTTPException(status_code=502, detail=str(e))


@MCPRouter.get("/api/prompts")
async def list_prompts():
    try:
        async with NanobotClient() as client:
            prompts = await client.list_prompts()
        return {"prompts": [p for p in prompts]}
    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@MCPRouter.post("/api/prompts/{name}")
async def get_prompt(name: str, body: dict = Body(None)):
    logger.info(f"[PROMPT DEBUG] Received body: {body}")
    arguments = {}
    if body:
        if "params" in body and isinstance(body["params"], dict) and "arguments" in body["params"]:
            arguments = body["params"]["arguments"]
        elif "arguments" in body:
            arguments = body["arguments"]
        else:
            arguments = body
    try:
        async with NanobotClient() as client:
            logger.info(f"[PROMPT DEBUG] Calling get_prompt with arguments: {arguments}")
            result = await client.get_prompt(name, arguments=arguments)
        logger.info(f"[PROMPT DEBUG] get_prompt result: {result}")
        return {"result": result}
    except Exception as e:
        logger.error(f"Prompt fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"{str(e)}: input: {arguments}")

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
                html_string = parsed.get("content", {}).get("htmlString")
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
    return await _get_ui_resource_helper(uri)

@TreadRouter.post("/api/resources/ui")
async def get_ui_resource_endpoint(request: Request, body: dict = Body(...)):
    """
    FastAPI endpoint for fetching UI resources.
    Only supports 'ui://' URIs and returns the htmlString from the resource content.
    Always returns HTML content.
    """
    uri = body.get("uri")
    return await _get_ui_resource_helper(uri)


@TreadRouter.get("/api/templates")
async def list_resource_templates(request: Request):
    """
    Lists non-UI resource templates.
    Returns a JSON object with 'templates' key containing a list of templates or renders as HTML with a template.
    """
    try:
        async with NanobotClient() as client:
            if hasattr(client, "list_resource_templates"):
                templates = await client.list_resource_templates()
            else:
                templates = []
        # Remove UI templates if any are present
        filtered_templates = []
        for t in templates:
            if not hasattr(t, "uriTemplate") or not t.uriTemplate.startswith("ui://"):
                filtered_templates.append(t)
        templates = filtered_templates

        # Check for X-Template header for template rendering
        template_name = request.headers.get("X-Template")
        accept_header = request.headers.get("Accept", "")
        prefer_json = "application/json" in accept_header
        
        if template_name and "text/html" in accept_header:
            # Use the UI resource system to get rendered template
            uri = f"ui://app/resource_templates"
            return await _get_ui_resource_helper(uri)
        elif prefer_json:
            return {"success": True, "templates": templates}
        else:
            # Default to HTML for backward compatibility
            return {"templates": templates}
    except Exception as e:
        logger.error(f"Error listing resource templates: {e}")
        accept_header = request.headers.get("Accept", "")
        prefer_json = "application/json" in accept_header
        if prefer_json:
            return {"success": False, "error": str(e), "templates": []}
        else:
            raise HTTPException(status_code=502, detail=str(e))

@TreadRouter.post("/api/chat")
async def chat_tool_call(request: Request, body: dict = Body(...)):
    """
    Calls the 'app' tool with a prompt and returns only the text response as HTML <p>...</p>.
    Accepts either {"prompt": "..."} or the full JSON-RPC style: {"method": "tools/call", "params": {"name": "app", "arguments": {"prompt": "..."}}}
    """
    # Support both direct and JSON-RPC style input
    logger.info(f"BODY RECEIVED: {body}")
    if "prompt" in body:
        prompt = body["prompt"]
    elif body.get("method") == "tools/call" and "params" in body:
        params = body["params"]
        if params.get("name") == "app" and "arguments" in params and "prompt" in params["arguments"]:
            prompt = params["arguments"]["prompt"]
        else:
            raise HTTPException(status_code=400, detail="Invalid params for chat tool call")
    else:
        raise HTTPException(status_code=400, detail="Missing 'prompt' or invalid input format")
    
    accept_header = request.headers.get("Accept", "")
    prefer_json = "application/json" in accept_header
    
    try:
        async with NanobotClient() as client:
            result = await client.call_tool("app", {"prompt": prompt})
        
        # Expecting result as list of message dicts, just like before
        response_text = None
        if isinstance(result, list) and result:
            for item in result:
                item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
                item_text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if item_type == "text" and item_text:
                    response_text = item_text
                    break
        
        if not response_text:
            response_text = "No response"
        
        if prefer_json:
            return {"success": True, "response": response_text, "prompt": prompt}
        else:
            # Return a generic class (not Tailwind-specific), e.g.:
            return HTMLResponse(
                f'''
                <div class="chat-bubble chat-bubble-bot">{response_text}</div>
                '''
            )
    except Exception as e:
        logger.error(f"Chat tool call failed: {e}")
        if prefer_json:
            return {"success": False, "error": str(e), "prompt": prompt}
        else:
            raise HTTPException(status_code=502, detail=str(e))

@TreadRouter.post("/api/prompts/{name}/messages")
async def get_rendered_prompt_messages(request: Request, name: str, body: dict = Body(...)):
    arguments = {}
    if body:
        if "params" in body and isinstance(body["params"], dict) and "arguments" in body["params"]:
            arguments = body["params"]["arguments"]
        elif "arguments" in body:
            arguments = body["arguments"]
        else:
            arguments = body
    
    accept_header = request.headers.get("Accept", "")
    prefer_json = "application/json" in accept_header
    
    try:
        async with NanobotClient() as client:
            result = await client.get_prompt(name, arguments=arguments)
        
        # ---- Extraction logic ----
        extracted_text = None
        
        # If result has attribute 'messages' (not dict), extract from first message
        if hasattr(result, "messages") and isinstance(result.messages, list):
            first_msg = result.messages[0]
            # For objects like PromptMessage, get .content and then .text
            if hasattr(first_msg, "content") and hasattr(first_msg.content, "text"):
                extracted_text = first_msg.content.text
            # Fallback for dict style
            elif isinstance(first_msg, dict):
                content = first_msg.get("content")
                if isinstance(content, dict):
                    text = content.get("text")
                    if text:
                        extracted_text = text
        # If result is a dict with 'messages'
        elif isinstance(result, dict) and "messages" in result:
            msgs = result["messages"]
            if isinstance(msgs, list) and msgs:
                msg = msgs[0]
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                if content:
                    text = content.get("text") if isinstance(content, dict) else getattr(content, "text", None)
                    if text:
                        extracted_text = text
        # If already string, just return
        elif isinstance(result, str):
            extracted_text = result
        
        # As a last resort, return stringified version
        if not extracted_text:
            extracted_text = str(result)
        
        if prefer_json:
            return {"success": True, "content": extracted_text, "prompt_name": name, "arguments": arguments}
        else:
            return HTMLResponse(extracted_text)
            
    except Exception as e:
        logger.error(f"Prompt rendered messages fetch failed: {e}")
        if prefer_json:
            return {"success": False, "error": str(e), "prompt_name": name, "arguments": arguments}
        else:
            raise HTTPException(status_code=502, detail=str(e))


@TreadRouter.post("/api/templates/message")
async def get_resource_with_instructions(request: Request, body: dict = Body(...)):
    """
    Accepts a URI directly in the request body along with optional user instructions.
    Retrieves the resource using the URI and sends it to the chat agent for a response.
    """
    uri = body.get("uri")
    instructions = body.get("instructions", "")
    
    accept_header = request.headers.get("Accept", "")
    prefer_json = "application/json" in accept_header
    
    if not uri:
        logger.error("Missing required 'uri' parameter")
        if prefer_json:
            return {"success": False, "error": "Missing required parameter: uri", "uri": None}
        else:
            return HTMLResponse(f'<div class="chat-bubble chat-bubble-bot text-red-500">Missing required parameter: uri</div>')
    
    # Now fetch the resource using the provided URI
    try:
        logger.info(f"Fetching resource from URI: {uri}")
        async with NanobotClient() as client:
            result = await client.read_resource(uri=uri)
        
        logger.info(f"Resource result: {result}")
        
        # Process the resource and instructions
        prompt_text = None
        if isinstance(result, list) and result:
            # Find the first text resource
            content = None
            for item in result:
                if hasattr(item, "text"):
                    content = getattr(item, "text")
                    break
            
            if content:
                content_obj = None
                try:
                    # Try to parse as JSON
                    content_obj = json.loads(content)
                except json.JSONDecodeError:
                    # If not JSON, use the raw content as text
                    logger.info("Content is not JSON, treating as plain text")
                    content_obj = {"text": content}
                except Exception as e:
                    logger.error(f"Error processing content: {e}")
                    if prefer_json:
                        return {"success": False, "error": f"Error processing content: {str(e)}", "uri": uri}
                    else:
                        return HTMLResponse(f'<div class="chat-bubble chat-bubble-bot text-red-500">Error processing content: {str(e)}</div>')
                
                if content_obj:
                    # Format the prompt for the chat agent
                    prompt_text = f"Resource from {uri}:\n\n"
                    
                    if isinstance(content_obj, dict):
                        if "text" in content_obj:
                            prompt_text += content_obj["text"]
                        else:
                            prompt_text += json.dumps(content_obj, indent=2)
                    else:
                        prompt_text += str(content_obj)
                    
                    # Add the instructions if provided
                    if instructions:
                        prompt_text += f"\n\nInstructions: {instructions}"
        
        # If we couldn't extract text or there was no proper response, return a generic message
        if not prompt_text:
            prompt_text = f"I'd like to know about the resource at {uri} {instructions}"
        
        if prefer_json:
            return {"success": True, "content": prompt_text, "uri": uri, "instructions": instructions}
        else:
            # Return the prompt text to be displayed in the user bubble
            # The frontend will use this to make a chat request
            return HTMLResponse(prompt_text)
            
    except Exception as e:
        logger.error(f"Error processing resource request: {e}")
        if prefer_json:
            return {"success": False, "error": str(e), "uri": uri, "instructions": instructions}
        else:
            return HTMLResponse(f'Error retrieving resource: {str(e)}')

# Export routers for use in main app
__all__ = ["MCPRouter", "TreadRouter", "get_ui_resource"]