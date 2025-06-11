import os
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Default template directory (can be overridden)
DEFAULT_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_template(template_name, context=None, template_dir=None):
    """Render a Jinja2 template with context."""
    template_path = template_dir or DEFAULT_TEMPLATE_DIR
    env = Environment(
        loader=FileSystemLoader(template_path),
        autoescape=select_autoescape(["html", "jinja", "tmpl"]),
    )
    template = env.get_template(template_name)
    return template.render(context or {})


def get_template_content(template_name, template_dir=None):
    """Get the raw template content without rendering."""
    template_path = template_dir or DEFAULT_TEMPLATE_DIR
    template_file = os.path.join(template_path, template_name)

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Template '{template_name}' not found in {template_path}"
        )
    except Exception as e:
        raise IOError(f"Error reading template '{template_name}': {e}")


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

    params = []
    pattern = r"{([^{}]*)}"
    matches = re.findall(pattern, uri_template)

    for match in matches:
        param_info = {"name": match, "required": True}

        if match.startswith("/"):
            param_name = match[1:]
            if param_name.endswith("*"):
                param_name = param_name[:-1]
                param_info["is_array"] = True
            param_info["name"] = param_name
            param_info["required"] = False
        elif match.endswith("?"):
            param_name = match[:-1]
            param_info["name"] = param_name
            param_info["required"] = False

        params.append(param_info)

    return params
