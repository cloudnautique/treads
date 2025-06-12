"""
Agent Configuration Loader

This module handles discovery and loading of agent configurations from
the agents/{name}/config.py files. It ensures all agent-specific Jinja
filters and globals are available globally.
"""

import os
import importlib.util
from typing import List, Dict, Any


def discover_and_load_agent_configs() -> List[Dict[str, Any]]:
    """
    Discover all agent configs in agents/{name}/config.py and load them.
    This ensures all agent-specific Jinja filters are available globally.
    
    Returns:
        List of loaded agent configurations with metadata
    """
    agents_dir = "agents"
    loaded_configs = []
    
    if not os.path.exists(agents_dir):
        print(f"ℹ No {agents_dir} directory found - skipping agent config discovery")
        return loaded_configs
    
    print(f"🔍 Discovering agent configs in {agents_dir}/")
    
    for agent_name in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, agent_name)
        config_path = os.path.join(agent_path, "config.py")
        
        if os.path.isdir(agent_path) and os.path.exists(config_path):
            try:
                config = _load_agent_config(agent_name, config_path)
                if config:
                    loaded_configs.append(config)
                    print(f"✓ Loaded config for {agent_name}")
                    
            except Exception as e:
                print(f"⚠ Error loading config for {agent_name}: {e}")
    
    print(f"📦 Loaded {len(loaded_configs)} agent configurations")
    return loaded_configs


def _load_agent_config(agent_name: str, config_path: str) -> Dict[str, Any] | None:
    """
    Load a single agent's configuration from its config.py file.
    
    Args:
        agent_name: Name of the agent
        config_path: Path to the agent's config.py file
        
    Returns:
        Configuration dictionary or None if loading failed
    """
    # Load the config module dynamically
    spec = importlib.util.spec_from_file_location(f"{agent_name}_config", config_path)
    if spec is None or spec.loader is None:
        print(f"⚠ Could not load spec for {agent_name}/config.py")
        return None
        
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    # Apply the agent's configuration
    if hasattr(config_module, 'apply_agent_config'):
        config = config_module.apply_agent_config()
        metadata = getattr(config_module, 'get_agent_metadata', lambda: {})()
        
        return {
            'agent': agent_name,
            'config': config,
            'metadata': metadata
        }
    else:
        print(f"⚠ {agent_name}/config.py missing apply_agent_config function")
        return None


def get_agent_config_summary(loaded_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get a summary of all loaded agent configurations.
    
    Args:
        loaded_configs: List of loaded agent configurations
        
    Returns:
        Summary dictionary with agent names, filters, and globals
    """
    summary = {
        'agents': [],
        'total_filters': 0,
        'total_globals': 0,
        'filters_by_agent': {},
        'globals_by_agent': {}
    }
    
    for config_info in loaded_configs:
        agent_name = config_info['agent']
        metadata = config_info.get('metadata', {})
        
        summary['agents'].append(agent_name)
        
        # Count filters and globals
        filters = metadata.get('filters', [])
        globals_list = metadata.get('globals', [])
        
        summary['total_filters'] += len(filters)
        summary['total_globals'] += len(globals_list)
        summary['filters_by_agent'][agent_name] = filters
        summary['globals_by_agent'][agent_name] = globals_list
    
    return summary
