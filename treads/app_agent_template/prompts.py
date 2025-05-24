from fastmcp import FastMCP


def register_prompts(mcp: FastMCP):
    @mcp.prompt()
    def app_prompt(text: str) -> str:
        """Describe what this prompt does."""
        return f"Prompt for app: {text} (stub)"
