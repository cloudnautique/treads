import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prompts import register_prompts
from resources import register_resources
from fastmcp import FastMCP

AGENT_NAME = "{name}_tools"

mcp = FastMCP(name=AGENT_NAME)
register_prompts(mcp)
register_resources(mcp)


@mcp.tool()
def agent_tool(text: str) -> str:
    """Describe what this tool does."""
    return f"{AGENT_NAME} tool called with: {text} (stub)"


if __name__ == "__main__":
    mcp.run()
