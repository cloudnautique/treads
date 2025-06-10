import os
from fastmcp import FastMCP
from treads.views.handlers import ResourceHandlers


def register_resources(mcp: FastMCP):
    """Register all UI resources - this is the only public interface."""
    
    # Configure handler with this agent's template directory
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    handlers = ResourceHandlers(template_dir)
    
    @mcp.resource("ui://app/{page}", mime_type="application/json",
                  description="Returns the HTML for a specific app page.")
    def app_ui(page: str):
        return handlers.app_page(page)

    @mcp.resource("ui://app/prompts", mime_type="application/json")
    async def app_ui_prompts():
        return await handlers.prompts_list()

    @mcp.resource("ui://app/prompts/{prompt_name}/form", mime_type="application/json")
    async def app_ui_prompt_form(prompt_name: str):
        return await handlers.prompt_form(prompt_name)

    @mcp.resource("ui://app/resource_templates", mime_type="application/json")
    async def app_ui_resource_templates():
        return await handlers.templates_list()

    @mcp.resource("ui://app/resource_templates/{template_name}/form", mime_type="application/json")
    async def app_ui_resource_template_form(template_name: str):
        return await handlers.template_form(template_name)