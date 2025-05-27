import os
import yaml
from pathlib import Path

ROOT = Path(__file__).parent
AGENTS_DIR = ROOT / "agents"
OUTPUT_YAML = ROOT / "nanobot.yaml"

# Instead of a global config, use the 'app' agent as the main config
MAIN_AGENT_NAME = "app"
MAIN_AGENT_YAML = AGENTS_DIR / MAIN_AGENT_NAME / "nanobot.yaml"


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def adjust_mcp_paths(agent_name, mcp_servers):
    # Adjust the command/args to run from the top level
    for server in mcp_servers.values():
        if not server:
            continue  # Skip None or empty server entries
        if "args" in server:
            new_args = []
            for arg in server["args"]:
                # Adjust any .py script to absolute agent path
                if arg.endswith(".py"):
                    new_args.append(str(AGENTS_DIR / agent_name / arg))
                else:
                    new_args.append(arg)
            server["args"] = new_args
    return mcp_servers


def merge_nanobot_yamls():
    merged = {
        "publish": {"tools": [], "prompts": [], "resources": [], "resourceTemplates": []},
        "agents": {},
        "mcpServers": {},
    }
    # Load main agent config if exists (app/agent/nanobot.yaml)
    if MAIN_AGENT_YAML.exists():
        main_yaml = load_yaml(MAIN_AGENT_YAML)
        for k in ["publish", "agents", "mcpServers"]:
            if k in main_yaml:
                if isinstance(main_yaml[k], dict):
                    if k == "publish":
                        # Merge tools, prompts, resources, and resourceTemplates
                        if "tools" in main_yaml[k]:
                            merged["publish"]["tools"].extend(main_yaml[k]["tools"])
                        if "prompts" in main_yaml[k]:
                            merged["publish"]["prompts"].extend(main_yaml[k]["prompts"])
                        if "resources" in main_yaml[k]:
                            merged["publish"]["resources"].extend(
                                main_yaml[k]["resources"]
                            )
                        if "resourceTemplates" in main_yaml[k]:
                            merged["publish"]["resourceTemplates"].extend(
                                main_yaml[k]["resourceTemplates"]
                            )
                    else:
                        merged[k].update(main_yaml[k])
                elif isinstance(main_yaml[k], list):
                    if k == "publish":
                        merged["publish"]["tools"].extend(main_yaml[k])
                    else:
                        merged[k]["tools"].extend(main_yaml[k])
    # Merge all agent nanobot.yaml files (including app)
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_yaml_path = agent_dir / "nanobot.yaml"
        if not agent_yaml_path.exists():
            continue
        agent_yaml = load_yaml(agent_yaml_path)
        # Merge publish tools, prompts, resources, and resourceTemplates
        if "publish" in agent_yaml:
            if "tools" in agent_yaml["publish"]:
                merged["publish"]["tools"].extend(agent_yaml["publish"]["tools"])
            if "prompts" in agent_yaml["publish"]:
                merged["publish"]["prompts"].extend(agent_yaml["publish"]["prompts"])
            if "resources" in agent_yaml["publish"]:
                merged["publish"]["resources"].extend(
                    agent_yaml["publish"]["resources"]
                )
            if "resourceTemplates" in agent_yaml["publish"]:
                merged["publish"]["resourceTemplates"].extend(
                    agent_yaml["publish"]["resourceTemplates"]
                )
        # Merge agents
        if "agents" in agent_yaml:
            merged["agents"].update(agent_yaml["agents"])
        # Merge and adjust mcpServers, omitting null/None
        if "mcpServers" in agent_yaml:
            adj = adjust_mcp_paths(agent_dir.name, agent_yaml["mcpServers"])
            for k, v in adj.items():
                if v is not None and isinstance(v, dict):
                    merged["mcpServers"][k] = v
    # Remove duplicates in publish.tools
    merged["publish"]["tools"] = list(sorted(set(merged["publish"]["tools"])))
    # Remove duplicates in publish.prompts (list of strings, including template placeholders)
    unique_prompts = []
    seen = set()
    for prompt in merged["publish"].get("prompts", []):
        if isinstance(prompt, str):
            if prompt not in seen:
                seen.add(prompt)
                unique_prompts.append(prompt)
        elif isinstance(prompt, dict) and len(prompt) == 1:
            key = next(iter(prompt))
            value = prompt[key]
            template_str = f"{{{key}}}" if value is None else str(value)
            if template_str not in seen:
                seen.add(template_str)
                unique_prompts.append(template_str)
    merged["publish"]["prompts"] = unique_prompts
    # Remove duplicates in publish.resources
    merged["publish"]["resources"] = list(
        sorted(set(merged["publish"].get("resources", [])))
    )
    # Remove duplicates in publish.resourceTemplates
    merged["publish"]["resourceTemplates"] = list(
        sorted(set(merged["publish"].get("resourceTemplates", [])))
    )
    # Set entrypoint: prefer agent value, fallback to app agent
    entrypoint = None
    # Check all agent yamls for entrypoint, last one wins
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_yaml_path = agent_dir / "nanobot.yaml"
        if not agent_yaml_path.exists():
            continue
        agent_yaml = load_yaml(agent_yaml_path)
        if "publish" in agent_yaml and "entrypoint" in agent_yaml["publish"]:
            entrypoint = agent_yaml["publish"]["entrypoint"]
    # If not found in agents, check app agent
    if not entrypoint and MAIN_AGENT_YAML.exists():
        main_yaml = load_yaml(MAIN_AGENT_YAML)
        if "publish" in main_yaml and "entrypoint" in main_yaml["publish"]:
            entrypoint = main_yaml["publish"]["entrypoint"]
    if entrypoint:
        merged["publish"]["entrypoint"] = entrypoint
    # Write merged nanobot.yaml with autogenerated comment
    with open(OUTPUT_YAML, "w") as f:
        f.write(
            "# DO NOT EDIT: This file is autogenerated by nanobot_template_util.py.\n"
        )
        yaml.dump(merged, f, sort_keys=False)
    print(f"Merged nanobot.yaml written to {OUTPUT_YAML}")


def merge_all_configs():
    """Alias for merge_nanobot_yamls for compatibility with app.py startup."""
    return merge_nanobot_yamls()


if __name__ == "__main__":
    merge_nanobot_yamls()
