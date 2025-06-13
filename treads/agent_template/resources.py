import os
from fastmcp import FastMCP
from treads.views.handlers import ResourceHandlers
from treads.views.services import PromptService, TemplateService


def register_resources(mcp: FastMCP):
    """Register all UI resources - this is the only public interface."""
    
    # Configure handler with this agent's template directory
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    handlers = ResourceHandlers(template_dir)
    
    @mcp.resource("ui://{name}/{page}", mime_type="application/json",
                  description="Returns the HTML for a specific {name} page.")
    def {name}_ui(page: str):
        return handlers.get_page(page)

    @mcp.resource("ui://{name}/prompts", mime_type="application/json")
    async def {name}_ui_prompts():
        return await handlers.prompts_list()

    @mcp.resource("ui://{name}/prompts/{prompt_name}/form", mime_type="application/json")
    async def {name}_ui_prompt_form(prompt_name: str):
        prompt = await PromptService.get_prompt(prompt_name)
        return await handlers.prompt_form(context=prompt)

    @mcp.resource("ui://{name}/resource_templates", mime_type="application/json")
    async def {name}_ui_resource_templates():
        return await handlers.templates_list()

    @mcp.resource("ui://{name}/resource_templates/{template_name}/form", mime_type="application/json")
    async def {name}_ui_resource_template_form(template_name: str):
        template = await TemplateService.get_template(template_name)
        return await handlers.template_form(context=template)

    @mcp.resource("ui://{name}/chat_response", mime_type="application/json",
                  description="Custom chat response template for {name} agent")
    def {name}_chat_response():
        # Return a simple JSON structure with the Jinja2 template
        return {
            "content": {
                "text": '''<div class="chat-bubble chat-bubble-bot bg-blue-50 border-l-4 border-blue-400 p-3 rounded-r-lg">
  <div class="flex items-center gap-2 mb-1">
    <span class="text-blue-600 font-semibold text-xs uppercase">{name} Agent</span>
    <span class="text-xs text-gray-500">{{ timestamp }}</span>
  </div>
  <div class="text-gray-800">{{ response | markdown }}</div>
</div>'''
            }
        }

    @mcp.resource("ui://{name}/error_response", mime_type="application/json",
                  description="Custom error response template for {name} agent")  
    def {name}_error_response():
        return {
            "content": {
                "text": '''<div class="chat-bubble chat-bubble-bot bg-red-50 border-l-4 border-red-400 p-3 rounded-r-lg">
  <div class="flex items-center gap-2 mb-1">
    <span class="text-red-600 font-semibold text-xs uppercase">{name} Agent - Error</span>
    <span class="text-xs text-gray-500">{{ timestamp }}</span>
  </div>
  <div class="text-red-800">{{ error }}</div>
</div>'''
            }
        }