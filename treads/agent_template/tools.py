from typing import Dict, Any
from fastmcp import FastMCP, Context


def register_tools(mcp: FastMCP) -> None:
    """Register tools for the {name} Agent."""
    @mcp.tool()
    async def chat(prompt: str, ctx: Context) -> str:
        """This tool chats with the {name} Agent."""
        result = await ctx.sample(prompt, model_preferences=f"{name}")

        return result.text

    @mcp.tool()
    async def render_template_from_string_tool(template_string: str, context: dict) -> Dict[str, Any]:
        """Render a template string with the given context."""
        agent = NanobotAgent(name="", dir="", address="")
        handlers = ResourceHandlers(agent, None)
        
        return handlers.render_template_from_string(template_string, context)