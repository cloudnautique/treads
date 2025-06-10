from treads.views.services import PromptService, TemplateService
from treads.views.template_utils import render_template, extract_uri_params


class HTMLTextType:
    """Class to represent HTML text type for content delivery."""
    def __init__(self, html_string: str):
        self.html_string = html_string
    
    def to_dict(self):
        return {"content": {"mimeType": "text/html", "text": self.html_string}}

class ResourceHandlers:
    def __init__(self, template_dir=None):
        """Initialize handlers with optional template directory."""
        self.template_dir = template_dir
    
    def _render(self, template_name, context=None):
        """Helper to render template with configured directory."""
        return render_template(template_name, context, self.template_dir)
    
    def get_page(self, page: str):
        """Render a simple app page."""
        html = self._render(f"{page}.html")
        return HTMLTextType(html).to_dict()
    
    async def prompts_list(self, template="prompts.tmpl"):
        """Render the prompts list page."""
        prompt_list, _ = await PromptService.get_prompts()
        html = self._render(template, {"prompts": prompt_list})
        return HTMLTextType(html).to_dict()
    
    async def prompt_form(self, prompt_name: str, template="prompt_form_modal.tmpl"):
        """Render a specific prompt form."""
        _, prompts_dict = await PromptService.get_prompts()
        prompt = prompts_dict.get(prompt_name)
        
        if not prompt:
            html = f"<div class='text-red-500'>Prompt '{prompt_name}' not found.</div>"
        else:
            prompt_dict = {
                "name": prompt_name,
                "description": prompt.description if hasattr(prompt, 'description') and prompt.description else "",
                "arguments": [arg.model_dump() for arg in prompt.arguments] if hasattr(prompt, 'arguments') and prompt.arguments else [],
            }
            html = self._render(template, {"prompt": prompt_dict})
        
        return HTMLTextType(html).to_dict()
    
    async def templates_list(self, template="resource_templates.tmpl"):
        """Render the resource templates list page."""
        template_list, _ = await TemplateService.get_templates()
        html = self._render(template, {"templates": template_list})
        return HTMLTextType(html).to_dict()
    
    async def template_form(self, template_name: str):
        """Render a specific template form."""
        _, templates_dict = await TemplateService.get_templates()
        template = templates_dict.get(template_name)
        
        if not template:
            html = f"<div class='text-red-500'>Template '{template_name}' not found.</div>"
        else:
            template_dict = {
                "name": template_name,
                "description": template.description if hasattr(template, 'description') and template.description else "",
                "arguments": [arg.model_dump() for arg in template.arguments] if hasattr(template, 'arguments') and template.arguments else [],
                "uriTemplate": template.uriTemplate if hasattr(template, 'uriTemplate') else None,
            }
            uri_params = extract_uri_params(template.uriTemplate)
            html = self._render("resource_template_form_modal.tmpl", {
                "template": template_dict, 
                "uri_params": uri_params
            })
        
        return HTMLTextType(html).to_dict()
