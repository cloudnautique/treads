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
        async with NanobotClient() as client:
            result = await client.read_resource(uri=uri)
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
    try:
        async with NanobotClient() as client:
            result = await client.call_tool("app", {"prompt": prompt})
        # Expecting result as list of message dicts, just like before
        if isinstance(result, list) and result:
            for item in result:
                item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
                item_text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if item_type == "text" and item_text:
                    # Return a generic class (not Tailwind-specific), e.g.:
                    return HTMLResponse(
                        f'''
                        <div class="chat-bubble chat-bubble-bot">{item_text}</div>
                        '''
                    )
        return HTMLResponse('<div class="chat-bubble chat-bubble-bot text-gray-400">No response</div>')
    except Exception as e:
        logger.error(f"Chat tool call failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@TreadRouter.post("/api/prompts/{name}/messages")
async def get_rendered_prompt_messages(name: str, body: dict = Body(...)):
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
            result = await client.get_prompt(name, arguments=arguments)
        # ---- Extraction logic ----
        # If result has attribute 'messages' (not dict), extract from first message
        if hasattr(result, "messages") and isinstance(result.messages, list):
            first_msg = result.messages[0]
            # For objects like PromptMessage, get .content and then .text
            if hasattr(first_msg, "content") and hasattr(first_msg.content, "text"):
                return HTMLResponse(first_msg.content.text)
            # Fallback for dict style
            if isinstance(first_msg, dict):
                content = first_msg.get("content")
                if isinstance(content, dict):
                    text = content.get("text")
                    if text:
                        return HTMLResponse(text)
        # If result is a dict with 'messages'
        if isinstance(result, dict) and "messages" in result:
            msgs = result["messages"]
            if isinstance(msgs, list) and msgs:
                msg = msgs[0]
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                if content:
                    text = content.get("text") if isinstance(content, dict) else getattr(content, "text", None)
                    if text:
                        return HTMLResponse(text)
        # If already string, just return
        if isinstance(result, str):
            return HTMLResponse(result)
        # As a last resort, return stringified version (not ideal)
        return HTMLResponse(str(result))
    except Exception as e:
        logger.error(f"Prompt rendered messages fetch failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))

# Export routers for use in main app
__all__ = ["MCPRouter", "TreadRouter"]