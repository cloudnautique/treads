import sys
from pathlib import Path
from fastmcp import FastMCP, Context
from mcp.types import TextContent

# ToDo - can this be done at the module level?
sys.path.insert(0, str(Path(__file__).parent))
from prompts import register_prompts
from resources import register_resources

AGENT_NAME = "app_tools"

mcp = FastMCP(name=AGENT_NAME)
register_prompts(mcp)
register_resources(mcp)


@mcp.tool()
def chat(prompt: str, ctx: Context) -> str:
    """This tool chats with the App Agent."""
    result = ctx.sample(prompt)

    assert isinstance(result, TextContent)
    return result.text
    

if __name__ == "__main__":
    mcp.run()
