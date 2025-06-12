from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from typing import Optional, Dict, Any, Callable


class JinjaEnvironment:
    """Centralized Jinja environment for the application."""
    
    _instance: Optional['JinjaEnvironment'] = None
    
    def __init__(self, template_dir: Optional[str] = None):
        if JinjaEnvironment._instance is not None:
            raise RuntimeError("JinjaEnvironment is a singleton. Use get_instance() instead.")
        
        self._initialize(template_dir)
        JinjaEnvironment._instance = self
    
    @classmethod
    def get_instance(cls) -> 'JinjaEnvironment':
        """Get the singleton instance."""
        if cls._instance is None:
            raise RuntimeError("JinjaEnvironment not initialized. Call initialize() first.")
        return cls._instance
    
    @classmethod
    def initialize(cls, template_dir: Optional[str] = None) -> 'JinjaEnvironment':
        """Initialize the singleton instance."""
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._instance._initialize(template_dir)
        return cls._instance
    
    def _initialize(self, template_dir: Optional[str] = None):
        """Internal initialization method."""
        self.template_dir = template_dir or os.path.join(os.path.dirname(__file__), '..', 'agent_template', 'templates')
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        # Cache for multiple template directories
        self._env_cache = {self.template_dir: self.env}
    
    def get_env_for_template_dir(self, template_dir: str) -> Environment:
        """Get or create a Jinja environment for a specific template directory."""
        if template_dir not in self._env_cache:
            self._env_cache[template_dir] = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            # Copy filters and globals from main environment
            self._env_cache[template_dir].filters.update(self.env.filters)
            self._env_cache[template_dir].globals.update(self.env.globals)
        return self._env_cache[template_dir]
    
    def add_filter(self, name: str, filter_func: Callable) -> None:
        """Add a custom filter to all Jinja environments."""
        self.env.filters[name] = filter_func
        # Update all cached environments
        for env in self._env_cache.values():
            env.filters[name] = filter_func
    
    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable to all Jinja environments."""
        self.env.globals[name] = value
        # Update all cached environments
        for env in self._env_cache.values():
            env.globals[name] = value
    
    def render_template(self, template_name: str, context: Optional[Dict[str, Any]] = None, template_dir: Optional[str] = None) -> str:
        """Render a template with the given context from a specific template directory."""
        if template_dir:
            env = self.get_env_for_template_dir(template_dir)
        else:
            env = self.env
        template = env.get_template(template_name)
        return template.render(context or {})
    
    def get_template_content(self, template_name: str, template_dir: Optional[str] = None) -> str:
        """Get raw template content without rendering from a specific template directory."""
        if template_dir:
            env = self.get_env_for_template_dir(template_dir)
        else:
            env = self.env
        if env.loader is None:
            raise RuntimeError("No loader configured for Jinja environment")
        source, _, _ = env.loader.get_source(env, template_name)
        return source


# Global instance accessor
def get_jinja_env() -> JinjaEnvironment:
    """Get the global Jinja environment instance."""
    if JinjaEnvironment._instance is None:
        # Auto-initialize if not already done
        JinjaEnvironment.initialize()
    return JinjaEnvironment.get_instance()
