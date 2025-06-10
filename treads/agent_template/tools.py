import logging
from fastmcp import FastMCP, Context

try:
    from .prompts import register_prompts
    from .resources import register_resources
except ImportError:
    from prompts import register_prompts
    from resources import register_resources

AGENT_NAME = "{name}_tools"


def create_agent() -> FastMCP:
    mcp = FastMCP(name=AGENT_NAME)
    register_prompts(mcp)
    register_resources(mcp)
    return mcp


logger = logging.getLogger("treads.agent.{name}.tools")


def setup_logging():
    logging.basicConfig(level=logging.INFO)


mcp = create_agent()


@mcp.tool()
async def chat(prompt: str, ctx: Context) -> str:
    """This tool chats with the {name} Agent."""
    result = await ctx.sample(prompt)

    return result.text


if __name__ == "__main__":
    setup_logging()
    mcp.run()
