import logging
from fastmcp import FastMCP, Context

try:
    from .prompts import register_prompts
    from .resources import register_resources
    from .config import apply_agent_config
except ImportError:
    from prompts import register_prompts
    from resources import register_resources
    try:
        from config import apply_agent_config
    except ImportError:
        apply_agent_config = None

AGENT_NAME = "{name}_tools"


def load_agent_config():
    """Load this agent's configuration."""
    if apply_agent_config:
        try:
            config = apply_agent_config()
            logger.info(f"Loaded configuration for {AGENT_NAME}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load agent config: {e}")
    else:
        logger.debug(f"No config.py found for {AGENT_NAME}")
    return None


def create_agent() -> FastMCP:
    # Load agent-specific configuration
    load_agent_config()
    
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
