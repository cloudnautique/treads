"""
Treads API Routers Package

This package contains the API routers for the Treads application:
- MCPRouter: Handles Model Context Protocol (MCP) related endpoints
- TreadRouter: Handles Treads-specific endpoints and UI resources
"""

from .tread import TreadRouter

__all__ = ["TreadRouter"]
