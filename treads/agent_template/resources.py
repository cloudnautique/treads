import os
from fastmcp import FastMCP
from treads.types import NanobotAgent
from treads.views.handlers import ResourceHandlers
from treads.views.types import HTMLTemplate
from treads.nanobot.client import NanobotAgentClient  # Ensure this is imported correctly


def register_resources(mcp: FastMCP, agent: NanobotAgent):
    """Register all UI resources - this is the only public interface."""
    
    # Configure handler with this agent's template directory
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    handlers = ResourceHandlers(agent, template_dir)
    agent = agent
    
    @mcp.resource("ui://{name}/{page}.html", mime_type="application/json",
                  description="Returns the HTML for a specific {name} page.")
    def {name}_ui(page: str):
        return handlers.get_page(f"{page}.html")

    @mcp.resource("ui://{name}/prompts", mime_type="application/json")
    async def {name}_ui_prompts():
        template = handlers.get_template_content(template_name="prompts.tmpl")
        return template.model_dump()

    @mcp.resource("ui://{name}/resource_templates", mime_type="application/json")
    async def {name}_ui_resource_templates():
        template = handlers.get_template_content(template_name="resource_templates.tmpl")
        return template.model_dump()

    @mcp.resource("ui://{name}/prompts/{prompt_name}/form", mime_type="application/json")
    async def {name}_ui_prompt_form(prompt_name: str):
        template = handlers.get_template_content(template_name="prompt_form.tmpl")
        return template.model_dump()

    @mcp.resource("ui://{name}/resource_templates/{template_name}/form", mime_type="application/json")
    async def {name}_ui_resource_template_form(template_name: str):
        template = await handlers.get_resource_template(name=template_name)
        if template is None:
            return {"error": "Template not found", "success": False}
        html = handlers.get_resource_template_form(template="resource_template_form.tmpl", context={"uriTemplate": f"{template.uriTemplate}"})
        return html

    @mcp.resource("ui://{name}/chat_response", mime_type="application/json",
                  description="Custom chat response template for {name} agent")
    def {name}_chat_response():
        # Return a simple JSON structure with the Jinja2 template
        template_content='''<div class="chat-bubble chat-bubble-bot bg-blue-50 border-l-4 border-blue-400 p-3 rounded-r-lg">
  <div class="flex items-center gap-2 mb-1">
    <span class="text-blue-600 font-semibold text-xs uppercase">{name} Agent</span>
    <span class="text-xs text-gray-500">{{ timestamp }}</span>
  </div>
  <div class="text-gray-800">{{ response }}</div>
</div>'''
        return HTMLTemplate(htmlTemplateString=template_content)

    @mcp.resource("ui://{name}/error_response", mime_type="application/json",
                  description="Custom error response template for {name} agent")  
    def {name}_error_response():
        template_content='''<div class="chat-bubble chat-bubble-bot bg-red-50 border-l-4 border-red-400 p-3 rounded-r-lg">
  <div class="flex items-center gap-2 mb-1">
    <span class="text-red-600 font-semibold text-xs uppercase">{name} Agent - Error</span>
    <span class="text-xs text-gray-500">{{ timestamp }}</span>
  </div>
  <div class="text-red-800">{{ error }}</div>
</div>'''
        return HTMLTemplate(htmlTemplateString=template_content)