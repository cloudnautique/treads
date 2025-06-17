import logging
from pathlib import Path

from treads.api.fastapp import load_default_app_config
from treads.api.helper import fetch_and_render_ui_resource
from treads.nanobot.client import register_agent  # Register agents at startup
from agents.app.agent import Agent as app_agent

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

agents = [
    app_agent,
]

# Register agents at startup
for agent in agents:
    register_agent(agent.name, agent)

def create_app():
    app = load_default_app_config(agents=agents)
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app

app = create_app()

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    return await fetch_and_render_ui_resource("ui://app/base.html")