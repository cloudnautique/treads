"""
Example of how to add custom Jinja filters and globals after initialization.

This file demonstrates how to extend the centralized Jinja environment
with custom filters and global variables after the application starts.

The system now supports dynamic template directories, so each agent can
have its own template directory while sharing the same filters and globals.
"""

from treads.views.jinja_env import get_jinja_env
from treads.views.handlers import ResourceHandlers


def setup_custom_filters():
    """Add custom filters and globals to the Jinja environment."""
    jinja_env = get_jinja_env()
    
    # Example custom filters
    def custom_format(value):
        """Format a value with custom prefix."""
        return f"Custom: {value}"
    
    def uppercase_words(text):
        """Convert each word to uppercase."""
        return ' '.join(word.upper() for word in str(text).split())
    
    def truncate_smart(text, length=50):
        """Smart truncation that doesn't break words."""
        if len(str(text)) <= length:
            return text
        return str(text)[:length].rsplit(' ', 1)[0] + '...'
    
    # Add the filters (will be available in all template directories)
    jinja_env.add_filter('custom_format', custom_format)
    jinja_env.add_filter('uppercase_words', uppercase_words)
    jinja_env.add_filter('truncate_smart', truncate_smart)
    
    # Example global variables (will be available in all template directories)
    jinja_env.add_global('app_version', '1.0.0')
    jinja_env.add_global('app_name', 'Nano Rails')
    jinja_env.add_global('debug_mode', False)


def example_usage():
    """Example of how to use ResourceHandlers with different template directories."""
    
    # Handler for the main app templates
    main_handlers = ResourceHandlers()  # Uses default template directory
    
    # Handler for a specific agent's templates
    agent_template_dir = "/path/to/agent/templates"
    agent_handlers = ResourceHandlers(template_dir=agent_template_dir)
    
    # Both handlers will have access to the same custom filters and globals
    # but will load templates from their respective directories


# Call this function after the Jinja environment is initialized
# For example, in your server.py after JinjaEnvironment.initialize()
if __name__ == "__main__":
    # This would be called after JinjaEnvironment.initialize()
    setup_custom_filters()
    print("Custom filters and globals added to Jinja environment")
    print("All ResourceHandlers will now have access to these filters")
