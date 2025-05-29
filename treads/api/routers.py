import os
import logging
import json

from fastapi import HTTPException, Body, Request, Query, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastapi.encoders import jsonable_encoder

from sse_starlette.sse import EventSourceResponse

NANOBOT_MCP_URL = os.environ.get("NANOBOT_MCP_URL", "http://localhost:8099/mcp")
logger = logging.getLogger("treads.api.routers")
logging.basicConfig(level=logging.INFO)

mcp_client = Client(StreamableHttpTransport(url=NANOBOT_MCP_URL))

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
        async with Client(StreamableHttpTransport(url=NANOBOT_MCP_URL)) as client:
            result = await client.read_resource(uri)
            logger.info(f"Fetched resource: {result}")
        return JSONResponse(content=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error fetching resource: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@MCPRouter.get("/api/resources")
async def list_resources():
    try:
        async with mcp_client:
            if hasattr(mcp_client, "list_resources"):
                resources = await mcp_client.list_resources()
            else:
                resources = []
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@MCPRouter.get("/api/tools")
async def list_tools():
    try:
        async with mcp_client:
            if hasattr(mcp_client, "list_tools"):
                tools = await mcp_client.list_tools()
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
                async with Client(StreamableHttpTransport(url=NANOBOT_MCP_URL)) as client:
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
            async with Client(StreamableHttpTransport(url=NANOBOT_MCP_URL)) as client:
                result = await client.call_tool(tool_name, arguments)
            return {"result": result}
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            raise HTTPException(status_code=502, detail=str(e))


@MCPRouter.get("/api/prompts")
async def list_prompts():
    try:
        async with mcp_client:
            prompts = await mcp_client.list_prompts()
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
        async with mcp_client:
            logger.info(f"[PROMPT DEBUG] Calling get_prompt with arguments: {arguments}")
            result = await mcp_client.get_prompt(name, arguments=arguments)
        logger.info(f"[PROMPT DEBUG] get_prompt result: {result}")
        return {"result": result}
    except Exception as e:
        logger.error(f"Prompt fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"{str(e)}: input: {arguments}")

# TreadRouter endpoints
@TreadRouter.post("/api/resources/ui")
async def get_ui_resource(body: dict = Body(...)):
    """
    Fetches a UI resource based on the provided body.
    Only supports 'ui://' URIs and returns the htmlString from the resource content.
    """
    uri = body.get("uri")
    logger.info(f"Received body for UI resource: {uri}")
    if not uri or not uri.startswith("ui://"):
        raise HTTPException(status_code=400, detail="Missing or invalid 'uri' (must start with 'ui://')")
    try:
        async with mcp_client:
            result = await mcp_client.read_resource(uri=uri)
        # result is a list of TextResourceContents-like objects
        logger.info(f"Fetched UI resource: {result}")
        for item in result:
            text = getattr(item, "text", None)
            if not text:
                continue
            try:
                parsed = json.loads(text)
                logger.info(f"Parsed resource text: {parsed}")
                html_string = parsed.get("content", {}).get("htmlString")
                if html_string:
                    # Return as HTMLResponse to ensure correct content-type and rendering
                    return HTMLResponse(content=html_string)
            except Exception as e:
                logger.error(f"Error parsing resource text as JSON: {e}")
                continue
        raise HTTPException(status_code=404, detail="No htmlString found in resource contents")
    except Exception as e:
        logger.error(f"Error fetching UI resource: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@TreadRouter.post("/api/chat")
async def chat_tool_call(body: dict = Body(...)):
    """
    Calls the 'app' tool with a prompt and returns only the text response as HTML <p>...</p>.
    Accepts either {"prompt": "..."} or the full JSON-RPC style: {"method": "tools/call", "params": {"name": "app", "arguments": {"prompt": "..."}}}
    """
    # Support both direct and JSON-RPC style input
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
    try:
        async with Client(StreamableHttpTransport(url=NANOBOT_MCP_URL)) as client:
            result = await client.call_tool("app", {"prompt": prompt})
        # result is expected to be a list of dicts or objects with 'type' and 'text'
        if isinstance(result, list) and result:
            for item in result:
                # Support both dict and object
                item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
                item_text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if item_type == "text" and item_text:
                    return HTMLResponse(f'<div class="chat-response">{item_text}</div>')
        return HTMLResponse("<p>No response</p>")
    except Exception as e:
        logger.error(f"Chat tool call failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@TreadRouter.post("/api/prompts/{name}/messages")
async def get_rendered_prompt_messages(name: str, body: dict = Body(...)):
    """
    Helper route: POST /api/prompts/{name}/messages
    Accepts the same input as /api/prompts/{name},
    returns only the 'messages' from the result as a hidden div for HTMX swap.
    """
    arguments = {}
    if body:
        if "params" in body and isinstance(body["params"], dict) and "arguments" in body["params"]:
            arguments = body["params"]["arguments"]
        elif "arguments" in body:
            arguments = body["arguments"]
        else:
            arguments = body
    try:
        async with mcp_client:
            result = await mcp_client.get_prompt(name, arguments=arguments)
        if result is None:
            raise HTTPException(status_code=502, detail="No messages in prompt result")
        return result
    except Exception as e:
        logger.error(f"Prompt rendered messages fetch failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))

# Export routers for use in main app
__all__ = ["MCPRouter", "TreadRouter"]