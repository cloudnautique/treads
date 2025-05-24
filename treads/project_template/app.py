from fastapi import FastAPI, Request
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import openai
import subprocess
import signal
from fastapi import status
from contextlib import asynccontextmanager

# Configuration (could be loaded from a config file or env)
NANOBOT_MCP_URL = os.environ.get("NANOBOT_MCP_URL", "http://localhost:8099/mcp")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

openai.api_key = OPENAI_API_KEY

# Use explicit StreamableHttpTransport for Nanobot MCP server
mcp_client = Client(StreamableHttpTransport(url=NANOBOT_MCP_URL))
templates = Jinja2Templates(directory="templates")

nanobot_process = None


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
