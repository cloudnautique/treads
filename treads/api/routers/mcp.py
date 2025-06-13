import logging
import json
from datetime import datetime

from fastapi import HTTPException, Body, Request, Query, APIRouter
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from sse_starlette.sse import EventSourceResponse
from treads.nanobot.client import NanobotClient
from treads.api.helper import (
    handle_client_operation,
    handle_client_list_operation,
    extract_arguments_from_body,
    extract_text_response_from_tool_result,
)

logger = logging.getLogger("treads.api.routers.mcp")
logging.basicConfig(level=logging.INFO)

MCPRouter = APIRouter()

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


__all__ = ["MCPRouter"]
