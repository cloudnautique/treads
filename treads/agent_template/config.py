"""
Agent Configuration for {name}

This file defines Jinja filters, globals, and other configuration
specific to the {name} agent. It will be loaded by both the web server
and the MCP server to ensure consistent behavior.
"""

import logging

logger = logging.getLogger(__name__)


def configure_jinja_environment():
    """
    Configure Jinja environment with agent-specific filters and globals.
    
    Returns:
        dict: Configuration containing 'filters' and 'globals' keys
    """
    
    def agent_prefix_filter(text: str) -> str:
        """Add agent prefix to text."""
        return f"[{'{name}'.upper()}] {text}"
    
    def format_agent_data(data):
        """Format data in a way specific to this agent."""
        if isinstance(data, dict):
            return ", ".join(f"{k}: {v}" for k, v in data.items())
        elif isinstance(data, list):
            return " | ".join(str(item) for item in data)
        return str(data)
    
    def agent_highlight_filter(text: str, keyword: str = "{name}") -> str:
        """Highlight specific keywords in the text."""
        import re
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        return pattern.sub(f'<mark>\\g<0></mark>', str(text))
    
    def agent_status_badge(status: str) -> str:
        """Create a status badge for {name} agent."""
        status_colors = {
            'active': 'bg-green-100 text-green-800',
            'inactive': 'bg-gray-100 text-gray-800', 
            'error': 'bg-red-100 text-red-800',
            'processing': 'bg-blue-100 text-blue-800'
        }
        color = status_colors.get(status.lower(), 'bg-gray-100 text-gray-800')
        return f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {color}">{status}</span>'
    
    # Agent-specific filters
    filters = {
        'agent_prefix': agent_prefix_filter,
        'agent_format': format_agent_data,
        'agent_highlight': agent_highlight_filter,
        'status_badge': agent_status_badge,
    }
    
    # Agent-specific globals
    globals_dict = {
        'agent_name': '{name}',
        'agent_version': '1.0.0',
        'agent_description': 'A specialized agent for {name} tasks',
        'agent_capabilities': [
            'Data processing',
            'Template rendering', 
            'Custom filtering'
        ],
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
    config = configure_jinja_environment()
    return {
        'name': '{name}',
        'description': 'A specialized agent for {name} tasks',
        'version': '1.0.0',
        'filters': list(config['filters'].keys()),
        'globals': list(config['globals'].keys()),
        'capabilities': config['globals'].get('agent_capabilities', []),
    }


def apply_agent_config():
    """
    Apply this agent's configuration to the current Jinja environment.
    This is called by the server to load agent-specific configuration.
    """
    try:
        from treads.views.jinja_env import configure_agent_jinja
        
        config = configure_jinja_environment()
        
        # Use the new centralized configuration function
        configure_agent_jinja(
            agent_name='{name}',
            filters=config['filters'],
            globals_dict=config['globals']
        )
        
        logger.info(f"Successfully applied configuration for {'{name}'} agent")
        return config
        
    except ImportError as e:
        logger.error(f"Failed to import jinja configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to apply agent configuration: {e}")
        raise
