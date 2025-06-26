import logging
from pathlib import Path

from treads.api.fastapp import create_base_app
from treads.nanobot.client import register_agent  # Register agents at startup
from agents.app.agent import Agent as app_agent

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
    app = create_base_app(agents=agents)
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    # print the registered routes
    return app

app = create_app()