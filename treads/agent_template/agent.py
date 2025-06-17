import logging

from fastmcp import FastMCP
from treads.types import NanobotAgent

from .prompts import register_prompts
from .resources import register_resources
from .tools import register_tools

logger = logging.getLogger(__name__)

AGENT_NAME = "{name}_mcp"

Agent = NanobotAgent(
    name="{name}",
    dir=f"agents/{name}/nanobot.yaml",
    address="127.0.0.1:8099"
)


def create_agent() -> FastMCP:
    mcp = FastMCP(name=AGENT_NAME)
    register_tools(mcp)
    register_prompts(mcp)
    register_resources(mcp, agent=Agent)
    return mcp

def setup_logging():
    logging.basicConfig(level=logging.INFO)


mcp = create_agent()


if __name__ == "__main__":
    setup_logging()
    mcp.run()