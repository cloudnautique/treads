import os
import re
from fastmcp import FastMCP
from jinja2 import Environment, FileSystemLoader, select_autoescape
from treads.nanobot.client import NanobotClient

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_app_template(template, context=None):
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "jinja", "tmpl"]),
    )
    template = env.get_template(template)
    return template.render(context or {})


def extract_uri_params(uri_template):
    """
    Extract parameters from a URI template.
    Handles complex cases like:
    - repo://{owner}/{repo}/contents{/path*}
    - api://{service}/v1/{resource}/{id}
    
    Returns a list of parameter dicts with name and optional specifier info.
    """
    if not uri_template:
        return []
    
    # Find all parameter patterns in the URI template
    params = []
    pattern = r'{([^{}]*)}'
    matches = re.findall(pattern, uri_template)
    
    for match in matches:
        param_info = {"name": match, "required": True}
        
        # Handle special notation like "/path*" for optional parameters
        if match.startswith('/'):
            # This is a path-style parameter like {/path*}
            param_name = match[1:]  # Remove the leading '/'
            if param_name.endswith('*'):
                param_name = param_name[:-1]  # Remove the trailing '*'
                param_info["is_array"] = True
            param_info["name"] = param_name
            param_info["required"] = False  # Path parameters are typically optional
        
        # Handle other special notations if needed
        # e.g., if there's a parameter with a "?" like {param?}
        elif match.endswith('?'):
            param_name = match[:-1]  # Remove the trailing '?'
            param_info["name"] = param_name
            param_info["required"] = False
            
        params.append(param_info)
    
    return params


def get_prompt_dicts():
    """Helper to get all prompts as a list of dicts."""
    async def _get():
        async with NanobotClient() as client:
            prompts = await client.list_prompts() or []
        return [
            {
                "name": getattr(prompt, "name", None),
                "description": getattr(prompt, "description", "") or "",
                "arguments": [arg.model_dump() for arg in getattr(prompt, "arguments", []) or []],
            }
            for prompt in prompts
        ], {getattr(prompt, "name", None): prompt for prompt in prompts}
    return _get


async def get_template_dicts():
    """Helper to get all resource templates as a list of dicts."""
    async with NanobotClient() as client:
        templates = await client.list_resource_templates() or []
    return [
        {
            "name": getattr(template, "name", None),
            "description": getattr(template, "description", "") or "",
            "arguments": [arg.model_dump() for arg in getattr(template, "arguments", []) or []] if hasattr(template, "arguments") else [],
            "uriTemplate": getattr(template, "uriTemplate", None),
        }
        for template in templates
    ], {getattr(template, "name", None): template for template in templates}


def register_resources(mcp: FastMCP):
    @mcp.resource("ui://app/{page}", mime_type="application/json",
                  description="Returns the HTML for a specific app page.",
                  )
    def app_ui_root(page: str) -> dict:
        html = render_app_template(template=f"{page}.html")
        return {
            "content": {"type": "html", "htmlString": html},
            "delivery": "text",
        }

    @mcp.resource("ui://app/prompts", mime_type="application/json")
    async def app_ui_prompts():
        get_prompts = get_prompt_dicts()
        prompt_list, _ = await get_prompts()
        html = render_app_template("prompts.tmpl", {"prompts": prompt_list})
        return {
            "content": {"type": "html", "htmlString": html},
            "delivery": "text",
        }

    @mcp.resource("ui://app/prompts/{prompt_name}/form", mime_type="application/json")
    async def app_ui_prompt_form(prompt_name: str):
        get_prompts = get_prompt_dicts()
        _, prompts_dict = await get_prompts()
        prompt = prompts_dict.get(prompt_name)
        if not prompt:
            return {
                "content": {"type": "html", "htmlString": f"<div class='text-red-500'>Prompt '{prompt_name}' not found.</div>"},
                "delivery": "text",
            }
        prompt_dict = {
            "name": prompt_name,
            "description": getattr(prompt, "description", "") or "",
            "arguments": [arg.model_dump() for arg in getattr(prompt, "arguments", []) or []],
        }
        html = render_app_template("prompt_form_modal.tmpl", {"prompt": prompt_dict})
        return {
            "content": {"type": "html", "htmlString": html},
            "delivery": "text",
        }

    @mcp.resource("ui://app/resource_templates", mime_type="application/json")
    async def app_ui_resource_templates():
        template_list, _ = await get_template_dicts()
        html = render_app_template("resource_templates.tmpl", {"templates": template_list})
        return {
            "content": {"type": "html", "htmlString": html},
            "delivery": "text",
        }

    @mcp.resource("ui://app/resource_templates/{template_name}/form", mime_type="application/json")
    async def app_ui_resource_template_form(template_name: str):
        _, templates_dict = await get_template_dicts()
        template = templates_dict.get(template_name)
        if not template:
            return {
                "content": {"type": "html", "htmlString": f"<div class='text-red-500'>Template '{template_name}' not found.</div>"},
                "delivery": "text",
            }
        template_dict = {
            "name": template_name,
            "description": getattr(template, "description", "") or "",
            "arguments": [arg.model_dump() for arg in getattr(template, "arguments", []) or []] if hasattr(template, "arguments") else [],
            "uriTemplate": getattr(template, "uriTemplate", None),
        }
        uri_params = extract_uri_params(template.uriTemplate)
        html = render_app_template("resource_template_form_modal.tmpl", {"template": template_dict, "uri_params": uri_params})
        return {
            "content": {"type": "html", "htmlString": html},
            "delivery": "text",
        }