import sys
import logging
from pathlib import Path
from fastmcp import FastMCP, Context
from mcp.types import TextContent

# ToDo - can this be done at the module level?
# Order prompts before resources to ensure they are registered first
sys.path.insert(0, str(Path(__file__).parent))
from prompts import register_prompts
from resources import register_resources

AGENT_NAME = "app"

mcp = FastMCP(name=AGENT_NAME)
register_prompts(mcp)
register_resources(mcp)

logger = logging.getLogger("treads.agent.app.tools")
logging.basicConfig(level=logging.INFO)


@mcp.tool()
async def chat(prompt: str, ctx: Context) -> str:
    """This tool chats with the App Agent."""
    result = await ctx.sample(prompt)

    return result.text
    

if __name__ == "__main__":
    mcp.run()
