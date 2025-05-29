import os
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