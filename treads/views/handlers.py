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
    
    def render_template(self, template_name, context=None):
        """Render template with configured directory."""
        return render_template(template_name, context, self.template_dir)
    
    def get_page(self, page: str):
        """Render a simple app page."""
        html = self.render_template(f"{page}.html")
        return HTMLTextType(html).to_dict()
    
    async def prompts_list(self, template="prompts.tmpl"):
        """Render the prompts list page."""
        prompt_list, _ = await PromptService.get_prompts()
        html = self.render_template(template, {"prompts": prompt_list})
        return HTMLTextType(html).to_dict()
    
    async def prompt_form(self, template="prompt_form_modal.tmpl", context=None):
        """Render a specific prompt form."""
        if not context:
            html = f"<div class='text-red-500'>Prompt not found.</div>"
        else:
            html = self.render_template(template, {"prompt": context})
        
        return HTMLTextType(html).to_dict()
    
    async def templates_list(self, template="resource_templates.tmpl"):
        """Render the resource templates list page."""
        template_list, _ = await TemplateService.get_templates()
        html = self.render_template(template, {"templates": template_list})
        return HTMLTextType(html).to_dict()
    
    async def template_form(self, template: str = "resource_template_form_modal.tmpl", context=None): 
        """Render a specific template form."""
        if not context:
            html = f"<div class='text-red-500'>Template not found.</div>"
        else:
            uri_params = extract_uri_params(context.uriTemplate)
            html = self.render_template(template, {
                "template": context, 
                "uri_params": uri_params
            })
        
        return HTMLTextType(html).to_dict()
