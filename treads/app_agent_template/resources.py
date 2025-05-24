from fastmcp import FastMCP


def register_resources(mcp: FastMCP):
    @mcp.resource("ui://app/root")
    def app_ui_root():
        """Returns the primary page."""
        return {
            "content": {
                "type": "html",
                "htmlString": "<h1>Hello from app agent resource!</h1>",
            },
            "delivery": "text",
        }
