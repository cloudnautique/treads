from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import logging
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)


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
        # Add basic/common filters
        self._add_basic_filters()
        
        # Cache for multiple template directories
        self._env_cache = {self.template_dir: self.env}
        
        # Add a global for debugging: list of filter names
        self.env.globals['jinja_filters'] = list(self.env.filters.keys())
        for env in self._env_cache.values():
            env.globals['jinja_filters'] = list(env.filters.keys())
    
    def _add_basic_filters(self):
        """Add basic filters that should be available in all templates."""
        def markdown_filter(text: str) -> str:
            """Convert markdown to HTML with enhanced support."""
            try:
                import markdown
                return markdown.markdown(
                    str(text), 
                    extensions=['fenced_code', 'tables', 'toc']
                )
            except ImportError:
                logger.warning("markdown package not available, using basic fallback")
                # Better fallback with basic markdown-like formatting
                text = str(text)
                # Convert **bold** to <strong>
                import re
                text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
                # Convert *italic* to <em>
                text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
                # Convert `code` to <code>
                text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
                # Convert newlines to <br>
                text = text.replace('\n', '<br>')
                return text
        
        def json_filter(obj) -> str:
            """Convert object to formatted JSON string."""
            import json
            return json.dumps(obj, indent=2, default=str, ensure_ascii=False)
        
        def safe_filter(text: str) -> str:
            """Mark string as safe (don't escape HTML)."""
            from markupsafe import Markup
            return Markup(text)
        
        def debug_filter(obj) -> str:
            """Debug filter that prints the whole template context."""
            import json
            try:
                # Get the current template context from the Jinja2 evaluation context
                import inspect
                
                context_found = False
                for frame_info in inspect.stack():
                    frame = frame_info.frame
                    f_locals = frame.f_locals
                    
                    # Look for the template context in various ways
                    if 'context' in f_locals:
                        ctx = f_locals['context']
                        # If it's a Jinja2 Context object, get the vars
                        if hasattr(ctx, 'get_exported') and hasattr(ctx, 'vars'):
                            context_vars = dict(ctx.vars)
                            # Filter out Jinja2 built-ins but keep user variables
                            filtered_vars = {k: v for k, v in context_vars.items() 
                                           if not k.startswith('_') and 
                                              k not in ['range', 'dict', 'lipsum', 'cycler', 'joiner', 'namespace']}
                            debug_output = f"TEMPLATE CONTEXT:\n{json.dumps(filtered_vars, indent=2, default=str)}"
                            logger.info(f"Debug filter output: {debug_output}")
                            context_found = True
                            return f"<!-- DEBUG: {debug_output} -->"
                        elif isinstance(ctx, dict):
                            debug_output = f"TEMPLATE CONTEXT:\n{json.dumps(ctx, indent=2, default=str)}"
                            logger.info(f"Debug filter output: {debug_output}")
                            context_found = True
                            return f"<!-- DEBUG: {debug_output} -->"
                    
                    # Also check for 'l_' prefixed variables (Jinja2 compiled template locals)
                    template_vars = {k[2:]: v for k, v in f_locals.items() 
                                   if k.startswith('l_') and not k.startswith('l__')}
                    if template_vars and not context_found:
                        debug_output = f"TEMPLATE VARIABLES:\n{json.dumps(template_vars, indent=2, default=str)}"
                        logger.info(f"Debug filter output: {debug_output}")
                        context_found = True
                        return f"<!-- DEBUG: {debug_output} -->"
                
                # Fallback - show what we received and available context
                debug_output = f"DEBUG INPUT: {type(obj).__name__} = {repr(obj)}"
                logger.info(f"Debug filter fallback: {debug_output}")
                return f"<!-- DEBUG: {debug_output} -->"
                    
            except Exception as e:
                error_msg = f"DEBUG ERROR: {e}"
                logger.error(error_msg)
                return f"<!-- DEBUG ERROR: {error_msg} -->"
        
        def pretty_filter(obj) -> str:
            """Pretty print objects in a readable format."""
            import pprint
            return pprint.pformat(obj, indent=2, width=80)
        
        def truncate_filter(text: str, length: int = 100, end: str = "...") -> str:
            """Truncate text to specified length."""
            text = str(text)
            if len(text) <= length:
                return text
            return text[:length-len(end)] + end
        
        # Add filters to environment
        self.env.filters.update({
            'markdown': markdown_filter,
            'json': json_filter,
            'safe': safe_filter,
            'debug': debug_filter,
            'pretty': pretty_filter,
            'truncate': truncate_filter,
        })
        
        logger.info(f"Added {len(self.env.filters)} basic filters to Jinja environment")
    
    def get_env_for_template_dir(self, template_dir: str) -> Environment:
        """Get or create a Jinja environment for a specific template directory."""
        if template_dir not in self._env_cache:
            self._env_cache[template_dir] = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            # Copy filters and globals from main environment (includes basic filters)
            self._env_cache[template_dir].filters.update(self.env.filters)
            self._env_cache[template_dir].globals.update(self.env.globals)
        return self._env_cache[template_dir]
    
    def add_filter(self, name: str, filter_func: Callable, 
                   namespace: Optional[str] = None, overwrite: bool = True) -> None:
        """Add a custom filter to all Jinja environments with optional namespacing."""
        if namespace:
            filter_name = f"{namespace}_{name}" if not name.startswith(f"{namespace}_") else name
        else:
            filter_name = name
            
        # Check if filter already exists and handle overwrite
        if filter_name in self.env.filters and not overwrite:
            logger.warning(f"Filter '{filter_name}' already exists, skipping (overwrite=False)")
            return
            
        self.env.filters[filter_name] = filter_func
        # Update all cached environments
        for env in self._env_cache.values():
            env.filters[filter_name] = filter_func
        
        logger.debug(f"Added filter '{filter_name}' to Jinja environment")
    
    def add_global(self, name: str, value: Any, 
                   namespace: Optional[str] = None, overwrite: bool = True) -> None:
        """Add a global variable to all Jinja environments with optional namespacing."""
        if namespace:
            global_name = f"{namespace}_{name}" if not name.startswith(f"{namespace}_") else name
        else:
            global_name = name
            
        # Check if global already exists and handle overwrite
        if global_name in self.env.globals and not overwrite:
            logger.warning(f"Global '{global_name}' already exists, skipping (overwrite=False)")
            return
            
        self.env.globals[global_name] = value
        # Update all cached environments
        for env in self._env_cache.values():
            env.globals[global_name] = value
            
        logger.debug(f"Added global '{global_name}' to Jinja environment")
    
    def get_available_filters(self) -> Dict[str, Callable]:
        """Get all available filters in the environment."""
        return dict(self.env.filters)
    
    def get_available_globals(self) -> Dict[str, Any]:
        """Get all available globals in the environment."""
        return dict(self.env.globals)
    
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


# Global instance management
_global_jinja_env: Optional[JinjaEnvironment] = None


def get_jinja_env() -> JinjaEnvironment:
    """
    Get the global Jinja environment instance.
    Auto-initializes if not already initialized.
    """
    global _global_jinja_env
    if _global_jinja_env is None:
        _global_jinja_env = JinjaEnvironment.initialize()
        logger.info("Auto-initialized global Jinja environment")
    return _global_jinja_env


def initialize_jinja_env(template_dir: Optional[str] = None) -> JinjaEnvironment:
    """
    Explicitly initialize the global Jinja environment.
    This is preferred over auto-initialization for better control.
    """
    global _global_jinja_env
    if _global_jinja_env is not None:
        logger.warning("Jinja environment already initialized, returning existing instance")
        return _global_jinja_env
    
    _global_jinja_env = JinjaEnvironment.initialize(template_dir)
    logger.info(f"Initialized global Jinja environment with template_dir: {template_dir or 'default'}")
    return _global_jinja_env


def configure_agent_jinja(agent_name: str, filters: Dict[str, Callable], 
                         globals_dict: Dict[str, Any]) -> None:
    """
    Configure Jinja environment with agent-specific filters and globals.
    This is the main function that agent configs should use.
    """
    jinja_env = get_jinja_env()
    
    # Add filters with agent namespace to avoid conflicts
    for name, filter_func in filters.items():
        jinja_env.add_filter(name, filter_func, namespace=agent_name, overwrite=False)
    
    # Add globals with agent namespace
    for name, value in globals_dict.items():
        jinja_env.add_global(name, value, namespace=agent_name, overwrite=False)
    
    logger.info(f"Configured {len(filters)} filters and {len(globals_dict)} globals for agent '{agent_name}'")
