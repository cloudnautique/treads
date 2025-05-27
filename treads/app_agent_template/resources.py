import os
from fastmcp import FastMCP, Context
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_app_template(template="app.tmpl", context=None):
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "jinja", "tmpl"]),
    )
    template = env.get_template(template)
    return template.render(context or {})


def register_resources(mcp: FastMCP):
    @mcp.resource("ui://app/root")
    def app_ui_root():
        html = render_app_template()
        return {
            "content": {"type": "html", "htmlString": html},
            "delivery": "text",
        }

    @mcp.resource("ui://app/prompts")
    async def app_ui_prompts(ctx: Context):
        prompts_dict = await ctx.fastmcp.get_prompts() or {}
        prompt_list = [
            {
                "name": name,
                "description": getattr(prompt, "description", "") or "",
                "arguments": [arg.model_dump() for arg in getattr(prompt, "arguments", []) or []],
            }
            for name, prompt in prompts_dict.items()
        ]
        html = render_app_template("prompts.tmpl", {"prompts": prompt_list})
        return {
            "content": {"type": "html", "htmlString": html},
            "delivery": "text",
        }

    @mcp.resource("ui://app/prompt_form/{prompt_name}")
    async def app_ui_prompt_form(prompt_name: str, ctx: Context):
        prompts_dict = await ctx.fastmcp.get_prompts() or {}
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