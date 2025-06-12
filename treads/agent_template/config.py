"""
Agent Configuration for {name}

This file defines Jinja filters, globals, and other configuration
specific to the {name} agent. It will be loaded by both the web server
and the MCP server to ensure consistent behavior.
"""

def configure_jinja_environment():
    """
    Configure Jinja environment with agent-specific filters and globals.
    
    Returns:
        dict: Configuration containing 'filters' and 'globals' keys
    """
    
    def example_filter(text: str) -> str:
        """Example filter specific to {name} agent."""
        return f"[{'{name}'.upper()}] {text}"
    
    def format_agent_data(data):
        """Format data in a way specific to this agent."""
        if isinstance(data, dict):
            return ", ".join(f"{k}: {v}" for k, v in data.items())
        return str(data)
    
    # Agent-specific filters
    filters = {
        'agent_prefix': example_filter,
        'agent_format': format_agent_data,
    }
    
    # Agent-specific globals
    globals_dict = {
        'agent_name': '{name}',
        'agent_version': '1.0.0',
        'agent_description': 'A specialized agent for {name} tasks',
    }
    
    return {
        'filters': filters,
        'globals': globals_dict
    }


def get_agent_metadata():
    """
    Return metadata about this agent.
    Used by the server to discover agent capabilities.
    """
    return {
        'name': '{name}',
        'description': 'A specialized agent for {name} tasks',
        'version': '1.0.0',
        'filters': list(configure_jinja_environment()['filters'].keys()),
        'globals': list(configure_jinja_environment()['globals'].keys()),
    }


def apply_agent_config():
    """
    Apply this agent's configuration to the current Jinja environment.
    This is called by the server to load agent-specific configuration.
    """
    from treads.views.jinja_env import get_jinja_env
    
    config = configure_jinja_environment()
    jinja_env = get_jinja_env()
    
    # Add filters with agent namespace to avoid conflicts
    for name, filter_func in config['filters'].items():
        filter_name = f"{name}_{'{name}'}" if not name.startswith('{name}_') else name
        jinja_env.add_filter(filter_name, filter_func)
    
    # Add globals with agent namespace
    for name, value in config['globals'].items():
        global_name = f"{name}_{'{name}'}" if not name.startswith('{name}_') else name
        jinja_env.add_global(global_name, value)
    
    return config
