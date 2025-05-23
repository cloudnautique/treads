import os
import yaml
from pathlib import Path

ROOT = Path(__file__).parent
AGENTS_DIR = ROOT / "agents"
GLOBAL_YAML = ROOT / "nanobot_global.yaml"
OUTPUT_YAML = ROOT / "nanobot.yaml"

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
    merged = {"publish": {"tools": [], "prompts": [], "resources": []}, "agents": {}, "mcpServers": {}}
    # Load global config if exists
    if GLOBAL_YAML.exists():
        global_yaml = load_yaml(GLOBAL_YAML)
        for k in ["publish", "agents", "mcpServers"]:
            if k in global_yaml:
                if isinstance(global_yaml[k], dict):
                    if k == "publish":
                        # Merge tools, prompts, and resources
                        if "tools" in global_yaml[k]:
                            merged["publish"]["tools"].extend(global_yaml[k]["tools"])
                        if "prompts" in global_yaml[k]:
                            merged["publish"]["prompts"].extend(global_yaml[k]["prompts"])
                        if "resources" in global_yaml[k]:
                            merged["publish"]["resources"].extend(global_yaml[k]["resources"])
                    else:
                        merged[k].update(global_yaml[k])
                elif isinstance(global_yaml[k], list):
                    if k == "publish":
                        merged["publish"]["tools"].extend(global_yaml[k])
                    else:
                        merged[k]["tools"].extend(global_yaml[k])
    # Merge all agent nanobot.yaml files
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_yaml_path = agent_dir / "nanobot.yaml"
        if not agent_yaml_path.exists():
            continue
        agent_yaml = load_yaml(agent_yaml_path)
        # Merge publish tools, prompts, and resources
        if "publish" in agent_yaml:
            if "tools" in agent_yaml["publish"]:
                merged["publish"]["tools"].extend(agent_yaml["publish"]["tools"])
            if "prompts" in agent_yaml["publish"]:
                merged["publish"]["prompts"].extend(agent_yaml["publish"]["prompts"])
            if "resources" in agent_yaml["publish"]:
                merged["publish"]["resources"].extend(agent_yaml["publish"]["resources"])
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
    merged["publish"]["resources"] = list(sorted(set(merged["publish"].get("resources", []))))
    # Merge publish.entrypoint (str, prefer agent value, fallback to global, else None)
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
    # If not found in agents, check global
    if not entrypoint and GLOBAL_YAML.exists():
        global_yaml = load_yaml(GLOBAL_YAML)
        if "publish" in global_yaml and "entrypoint" in global_yaml["publish"]:
            entrypoint = global_yaml["publish"]["entrypoint"]
    if entrypoint:
        merged["publish"]["entrypoint"] = entrypoint
    # Write merged nanobot.yaml with autogenerated comment
    with open(OUTPUT_YAML, "w") as f:
        f.write("# DO NOT EDIT: This file is autogenerated by nanobot_template_util.py.\n")
        yaml.dump(merged, f, sort_keys=False)
    print(f"Merged nanobot.yaml written to {OUTPUT_YAML}")

def merge_all_configs():
    """Alias for merge_nanobot_yamls for compatibility with app.py startup."""
    return merge_nanobot_yamls()

if __name__ == "__main__":
    merge_nanobot_yamls()
