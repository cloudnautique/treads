import logging

from typing import Type, Optional
from pydantic import BaseModel, Field
from treads.views.template_utils import extract_uri_params
from treads.views.jinja_env import get_jinja_env
from treads.views.types import HTMLTextType, HTMLTemplate

logger = logging.getLogger(__name__)


class ResourceHandlers:
    def __init__(self, template_dir=None):
        """Initialize handlers with optional template directory."""
        self.template_dir = template_dir
    
    def render_template(self, template_name, context=None):
        """Render template using the global Jinja environment."""
        jinja_env = get_jinja_env()
        return jinja_env.render_template(template_name, context, self.template_dir)
    
    def get_page(self, page: str):
        """Render a simple app page."""
        html = self.render_template(f"{page}")
        return HTMLTextType(htmlString=html).model_dump()
    
    def get_template_content(
        self,
        template_name: str,
        context_schema: Optional[Type[BaseModel]] = None
    ) -> HTMLTemplate:
        """Get the raw template content without rendering."""
        jinja_env = get_jinja_env()
        template_content = jinja_env.get_template_content(template_name, self.template_dir)
        # context_schema is a Type[BaseModel] or None, but the model expects contextSchema
        schema = context_schema.model_json_schema() if context_schema and issubclass(context_schema, BaseModel) else (context_schema or {})
        return HTMLTemplate(htmlTemplateString=template_content, contextSchema=schema)

    def get_resource_template_form(self, template: str = "resource_template_form.tmpl", context=None): 
        """Render a resource template form. Handles the uriTemplate extraction."""
        if not context:
            html = f"<div class='text-red-500'>Template not found.</div>"
        else:
            logger.info(f"Rendering resource template form with context: {context}")
            uri_params = extract_uri_params(context["uriTemplate"])
            logger.info(f"Extracted URI params: {uri_params}")
            html = self.render_template(template, {
                "template": context, 
                "uri_params": uri_params
            })
        
        return HTMLTextType(htmlString=html).model_dump()
