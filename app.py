from fastapi import FastAPI, Request, Body
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
import openai
import subprocess
import signal
import logging
from fastapi import status

app = FastAPI()

# Configuration (could be loaded from a config file or env)
NANOBOT_MCP_URL = os.environ.get("NANOBOT_MCP_URL", "http://localhost:8099/mcp")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

openai.api_key = OPENAI_API_KEY

# Use explicit StreamableHttpTransport for Nanobot MCP server
mcp_client = Client(StreamableHttpTransport(url=NANOBOT_MCP_URL))
templates = Jinja2Templates(directory="templates")

nanobot_process = None

@app.on_event("startup")
def start_nanobot():
    global nanobot_process
    if nanobot_process is None:
        nanobot_process = subprocess.Popen([
            "nanobot", "run", ".", "--listen-address", "127.0.0.1:8099"
        ])

@app.on_event("shutdown")
def stop_nanobot():
    global nanobot_process
    if nanobot_process is not None:
        nanobot_process.send_signal(signal.SIGINT)
        nanobot_process.wait()
        nanobot_process = None

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    chat_response = request.query_params.get("chat_response")
    try:
        print(f"MCP Client is connected? {mcp_client.is_connected()}")
        async with mcp_client:
            print(f"MCP Client is connected? {mcp_client.is_connected()}")
            tools = await mcp_client.list_tools()
            print(f"Tools dump {tools}")
        return templates.TemplateResponse(
            "base.html",
            {
                "request": request,
                "message": "Welcome to nano-rails!",
                "openai_model": OPENAI_MODEL,
                "tools": [tool.name for tool in tools],
                "error": None,
                "chat_response": chat_response,
            }
        )
    except Exception as e:
        logging.exception("Failed to connect to MCP server or list tools")
        return templates.TemplateResponse(
            "base.html",
            {
                "request": request,
                "message": "Could not connect to MCP server or list tools.",
                "openai_model": OPENAI_MODEL,
                "tools": [],
                "error": str(e),
                "chat_response": chat_response,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.post("/chat")
async def chat_post(data: dict = Body(...)):
    prompt = data.get("prompt", "")
    messages = data.get("messages", [{"role": "user", "content": prompt}])
    tools = []
    try:
        async with mcp_client:
            mcp_tools = await mcp_client.list_tools()
            print(f"[DEBUG] MCP tools fetched: {mcp_tools}")
            for t in mcp_tools:
                tool_payload = {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": getattr(t, "description", ""),
                        "parameters": getattr(t, "inputSchema", {}) or {}
                    }
                }
                print(f"[DEBUG] Tool payload for OpenAI: {tool_payload}")
                tools.append(tool_payload)
    except Exception as e:
        logging.warning(f"Could not fetch tools for chat: {e}")
    print(f"[DEBUG] Final tools list sent to OpenAI: {tools}")
    # Call OpenAI with tools if any
    if tools:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
    else:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages
        )
    print(f"[DEBUG] OpenAI response: {response}")
    choice = response.choices[0]
    # Check for tool calls in the response
    if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
        print(f"[DEBUG] Tool calls in response: {choice.message.tool_calls}")
        tool_call = choice.message.tool_calls[0]
        tool_name = tool_call.function.name
        import json
        tool_args = json.loads(tool_call.function.arguments)
        print(f"[DEBUG] Forwarding tool call to MCP: {tool_name}({tool_args})")
        async with mcp_client:
            mcp_result = await mcp_client.call_tool(tool_name, tool_args)
            print(f"[DEBUG] MCP tool result: {mcp_result}")
        # Extract text from TextContent if present
        if mcp_result and hasattr(mcp_result[0], 'text'):
            return {"response": mcp_result[0].text}
        return {"response": str(mcp_result)}
    return {"response": choice.message.content}

@app.get("/prompts")
async def list_prompts():
    async with mcp_client:
        prompts = await mcp_client.list_prompts()
    return {"prompts": [p.name for p in prompts]}

@app.get("/resources")
async def list_resources():
    async with mcp_client:
        resources = await mcp_client.list_resources()
    return {"resources": [str(r.uri) for r in resources]}

@app.get("/resource/{uri:path}")
async def get_resource(uri: str):
    async with mcp_client:
        result = await mcp_client.read_resource(uri)
    return {"resource": result}

@app.get("/prompt/{name}")
async def get_prompt(name: str):
    async with mcp_client:
        prompt = await mcp_client.get_prompt(name)
    return {"prompt": prompt}
