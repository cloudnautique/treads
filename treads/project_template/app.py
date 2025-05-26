# Standard library imports
import os
import subprocess
import signal
import logging
from contextlib import asynccontextmanager

# Third-party imports
import openai
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# Configuration (could be loaded from a config file or env)
NANOBOT_MCP_URL = os.environ.get("NANOBOT_MCP_URL", "http://localhost:8099/mcp")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

openai.api_key = OPENAI_API_KEY

# Use explicit StreamableHttpTransport for Nanobot MCP server
mcp_client = Client(StreamableHttpTransport(url=NANOBOT_MCP_URL))
templates = Jinja2Templates(directory="templates")

nanobot_process = None

logger = logging.getLogger("treads.api")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global nanobot_process
    # Startup logic
    import nanobot_template_util

    nanobot_template_util.merge_all_configs()
    if nanobot_process is None:
        nanobot_process = subprocess.Popen(
            ["nanobot", "run", ".", "--mcp", "--listen-address", "127.0.0.1:8099"]
        )
    try:
        yield
    finally:
        # Shutdown logic
        if nanobot_process is not None:
            nanobot_process.send_signal(signal.SIGINT)
            nanobot_process.wait()
            nanobot_process = None


app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    # Serve the base.html template with minimal context
    return templates.TemplateResponse("base.html", {"request": request})


def render_ui_resource(result):
    # Only log at info level for key events
    # Handle pydantic model (TextResourceContents) as in the log
    import json as _json
    if (
        isinstance(result, list)
        and len(result) == 1
    ):
        item = result[0]
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text")
        if text:
            try:
                parsed = _json.loads(text)
                if (
                    isinstance(parsed, dict)
                    and "content" in parsed
                    and isinstance(parsed["content"], dict)
                    and parsed["content"].get("type") == "html"
                    and "htmlString" in parsed["content"]
                ):
                    logger.info("Returning HTML fragment for ui:// resource (pydantic/text)")
                    return parsed["content"]["htmlString"]
            except Exception:
                pass
    if (
        isinstance(result, dict)
        and "contents" in result
        and isinstance(result["contents"], list)
        and len(result["contents"]) == 1
        and isinstance(result["contents"][0], dict)
        and "text" in result["contents"][0]
    ):
        try:
            parsed = _json.loads(result["contents"][0]["text"])
            if (
                isinstance(parsed, dict)
                and "content" in parsed
                and isinstance(parsed["content"], dict)
                and parsed["content"].get("type") == "html"
                and "htmlString" in parsed["content"]
            ):
                logger.info("Returning HTML fragment for ui:// resource (dict/contents)")
                return parsed["content"]["htmlString"]
        except Exception:
            pass
    return None


@app.post("/api/resource")
async def get_resource(request: Request):
    # Only log the most important info
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
    uri = data.get("uri")
    if not uri:
        logger.warning("/api/resource missing 'uri' in request body")
        raise HTTPException(status_code=400, detail="Missing 'uri' in request body")
    try:
        async with Client(StreamableHttpTransport(url=NANOBOT_MCP_URL)) as client:
            result = await client.read_resource(uri)
        if uri.startswith("ui://"):
            html = render_ui_resource(result)
            if html is not None:
                return Response(content=html, media_type="text/html")
            return {"resource": result}
        if (
            isinstance(result, dict)
            and "content" in result
            and isinstance(result["content"], dict)
            and result["content"].get("type") == "html"
            and "htmlString" in result["content"]
        ):
            logger.info("Returning HTML fragment for dict-style html resource")
            return Response(content=result["content"]["htmlString"], media_type="text/html")
        return {"resource": result}
    except Exception as e:
        logger.error(f"MCP resource fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"MCP resource fetch failed: {e}")


def to_call_tool_result(result, is_error=False):
    """
    Convert a result to MCP CallToolResult format.
    """
    content_list = []
    if isinstance(result, list):
        for item in result:
            if hasattr(item, "text"):
                content_list.append({"type": "text", "text": item.text})
            elif hasattr(item, "url") and hasattr(item, "mime_type"):
                content_list.append({"type": "image", "data": item.url, "mimeType": item.mime_type})
            elif isinstance(item, dict):
                if "text" in item:
                    content_list.append({"type": "text", "text": item["text"]})
                elif "url" in item and "mime_type" in item:
                    content_list.append({"type": "image", "data": item["url"], "mimeType": item["mime_type"]})
                else:
                    content_list.append({"type": "text", "text": str(item)})
            else:
                content_list.append({"type": "text", "text": str(item)})
    elif isinstance(result, dict) and "content" in result:
        content_list.append(result["content"])
    else:
        content_list.append({"type": "text", "text": str(result)})
    return {"isError": is_error, "content": content_list}


@app.post("/api/tool-call")
async def tool_call(request: Request, stream: int = Query(0)):
    """
    Handle tool calls, supporting both streaming (SSE) and non-streaming modes.
    Progress events are not supported; only a single result is streamed if streaming is requested.
    """
    import json as _json
    from fastapi import Request
    from sse_starlette.sse import EventSourceResponse

    logger.info("/api/tool-call endpoint hit")
    # Accept both JSON and form data
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
    logger.info(f"Request data: {data}")

    method = data.get("method")
    params = data.get("params", {})
    meta = params.get("_meta", {})
    # Allow stream detection via query param, header, or _meta
    stream_requested = (
        stream == 1 or
        request.headers.get("x-stream", "0") == "1" or
        meta.get("stream", False)
    )
    logger.info(f"stream_requested: {stream_requested}")

    if method != "tools/call":
        logger.warning(f"/api/tool-call received invalid method: {method}")
        raise HTTPException(status_code=400, detail=f"Invalid method: {method}")

    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    logger.info(f"tool_name: {tool_name}, arguments: {arguments}")

    if not tool_name:
        logger.warning("/api/tool-call missing 'name' in params")
        raise HTTPException(status_code=400, detail="Missing 'name' in params")

    logger.info(f"Tool call: {tool_name} (stream={stream_requested}) with arguments: {arguments}")

    if stream_requested:
        sent = False
        async def event_generator():
            nonlocal sent
            if sent:
                return
            try:
                async with Client(StreamableHttpTransport(url=NANOBOT_MCP_URL)) as client:
                    result = await client.call_tool(tool_name, arguments)
                call_tool_result = to_call_tool_result(result)
                yield {"event": "complete", "data": _json.dumps(call_tool_result)}
            except Exception as e:
                yield {"event": "error", "data": _json.dumps(to_call_tool_result(str(e), is_error=True))}
            sent = True
        logger.info("Returning EventSourceResponse from /api/tool-call (no progress events)")
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
        logger.info("Non-streaming tool call")
        try:
            async with Client(StreamableHttpTransport(url=NANOBOT_MCP_URL)) as client:
                result = await client.call_tool(tool_name, arguments)
            call_tool_result = to_call_tool_result(result)
            logger.info(f"Returning result: {call_tool_result}")
            return call_tool_result
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}", exc_info=True)
            return to_call_tool_result(str(e), is_error=True)