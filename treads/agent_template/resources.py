from fastmcp import FastMCP


def register_resources(mcp: FastMCP):
    @mcp.resource("html://widget/hello")
    def hello_widget_resource():
        """Returns a raw HTML widget."""
        return {
            "content": {
                "type": "html",
                "htmlString": f"<p>Hello from {name} agent resource!</p>",
            },
            "delivery": "text",
        }
