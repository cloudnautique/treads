import os
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

NANOBOT_MCP_URL = os.environ.get("NANOBOT_MCP_URL", "http://localhost:8099/mcp")

def NanobotClient() -> Client:
    """Create a FastMCP client for the Nanobot MCP."""
    transport = StreamableHttpTransport(NANOBOT_MCP_URL)
    return Client(transport=transport)

__all__ = ["NanobotClient"]