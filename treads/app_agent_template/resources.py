import os
from fastmcp import FastMCP
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_app_template(context=None):
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "jinja", "tmpl"]),
    )
    template = env.get_template("app.tmpl")
    return template.render(context or {})


def register_resources(mcp: FastMCP):
    @mcp.resource("ui://app/root")
    def app_ui_root():
        """Returns the primary page."""
        html = render_app_template()
        return {
            "content": {
                "type": "html",
                "htmlString": html,
            },
            "delivery": "text",
        }
