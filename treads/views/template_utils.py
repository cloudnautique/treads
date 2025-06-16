import re
from typing import Any


def extract_uri_params(uri_template) -> list[dict[str, Any]]:
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
