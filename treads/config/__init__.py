"""
Treads Configuration Module

This module handles configuration loading and management for the treads framework.
"""

from .loader import discover_and_load_agent_configs, get_agent_config_summary

__all__ = [
    'discover_and_load_agent_configs',
    'get_agent_config_summary'
]
