"""
Agent Configuration Loader

This module handles discovery and loading of agent configurations from
the agents/{name}/config.py files. It ensures all agent-specific Jinja
filters and globals are available globally.
"""

import os
import logging
import importlib.util
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def discover_and_load_agent_configs() -> List[Dict[str, Any]]:
    """
    Discover all agent configs in agents/{name}/config.py and load them.
    This ensures all agent-specific Jinja filters are available globally.
    
    Returns:
        List of loaded agent configurations with metadata
    """
    # Initialize Jinja environment first
    from treads.views.jinja_env import initialize_jinja_env
    try:
        jinja_env = initialize_jinja_env()  # Use explicit initialization
        logger.info("✓ Jinja environment initialized successfully")
    except Exception as e:
        logger.error(f"⚠ Failed to initialize Jinja environment: {e}")
        return []
    
    agents_dir = "agents"
    loaded_configs = []
    
    if not os.path.exists(agents_dir):
        logger.info(f"ℹ No {agents_dir} directory found - skipping agent config discovery")
        return loaded_configs
    
    logger.info(f"🔍 Discovering agent configs in {agents_dir}/")
    
    for agent_name in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, agent_name)
        config_path = os.path.join(agent_path, "config.py")
        
        if os.path.isdir(agent_path) and os.path.exists(config_path):
            try:
                config = _load_agent_config(agent_name, config_path)
                if config:
                    loaded_configs.append(config)
                    logger.info(f"✓ Loaded config for {agent_name}")
                    
            except Exception as e:
                logger.error(f"⚠ Error loading config for {agent_name}: {e}")
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    if loaded_configs:
        logger.info(f"📦 Loaded {len(loaded_configs)} agent configurations")
        _print_config_summary(loaded_configs)
    else:
        logger.info("📦 No agent configurations loaded")
        
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
        logger.warning(f"⚠ Could not load spec for {agent_name}/config.py")
        return None
        
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    # Apply the agent's configuration
    if hasattr(config_module, 'apply_agent_config'):
        try:
            config = config_module.apply_agent_config()
            metadata = getattr(config_module, 'get_agent_metadata', lambda: {})()
            
            logger.info(f"  🔧 Applied configuration for {agent_name}")
            
            # Debug: Show what was applied
            if isinstance(config, dict):
                filters = config.get('filters', {})
                globals_dict = config.get('globals', {})
                if filters:
                    logger.debug(f"    ➕ Added {len(filters)} filters: {list(filters.keys())}")
                if globals_dict:
                    logger.debug(f"    ➕ Added {len(globals_dict)} globals: {list(globals_dict.keys())}")
            
            return {
                'agent': agent_name,
                'config': config,
                'metadata': metadata
            }
        except Exception as e:
            logger.error(f"⚠ Error applying config for {agent_name}: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return None
    else:
        logger.warning(f"⚠ {agent_name}/config.py missing apply_agent_config function")
        return None


def _print_config_summary(loaded_configs: List[Dict[str, Any]]) -> None:
    """Print a summary of loaded configurations."""
    total_filters = 0
    total_globals = 0
    
    for config_info in loaded_configs:
        metadata = config_info.get('metadata', {})
        filters = metadata.get('filters', [])
        globals_list = metadata.get('globals', [])
        total_filters += len(filters)
        total_globals += len(globals_list)
        
        agent_name = config_info['agent']
        if filters or globals_list:
            logger.info(f"  📋 {agent_name}: {len(filters)} filters, {len(globals_list)} globals")
            if filters:
                logger.debug(f"     🔧 Filters: {', '.join(filters)}")
            if globals_list:
                logger.debug(f"     🌐 Globals: {', '.join(globals_list)}")
    
    logger.info(f"📊 Total: {total_filters} filters, {total_globals} globals loaded")


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
