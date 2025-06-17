import os
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from treads.types import NanobotAgent

_agent_registry = {}

def register_agent(name, agent_obj):
    _agent_registry[name] = agent_obj

def get_agent(name):
    return _agent_registry.get(name)

def NanobotAgentClient(agent: NanobotAgent) -> Client:
    agent_url = f"http://{agent.address}/mcp"
    transport = StreamableHttpTransport(agent_url)
    return Client(transport=transport)

__all__ = ["register_agent", "get_agent", "NanobotAgentClient"]