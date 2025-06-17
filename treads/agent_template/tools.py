from fastmcp import FastMCP, Context


def register_tools(mcp: FastMCP) -> None:
    """Register tools for the {name} Agent."""
    @mcp.tool()
    async def chat(prompt: str, ctx: Context) -> str:
        """This tool chats with the {name} Agent."""
        result = await ctx.sample(prompt, model_preferences=f"{name}")

        return result.text