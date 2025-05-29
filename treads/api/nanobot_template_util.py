import os
import yaml
from pathlib import Path

# Always resolve project root as the current working directory
PROJECT_ROOT = Path.cwd()
AGENTS_DIR = PROJECT_ROOT / "agents"
OUTPUT_YAML = PROJECT_ROOT / "nanobot.yaml"

# Instead of a global config, use the 'app' agent as the main config
MAIN_AGENT_NAME = "app"
MAIN_AGENT_YAML = AGENTS_DIR / MAIN_AGENT_NAME / "nanobot.yaml"

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def adjust_mcp_paths(agent_name, mcp_servers):
    for server in mcp_servers.values():
        if not server:
            continue
        if "args" in server:
            new_args = []
            for arg in server["args"]:
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
    if MAIN_AGENT_YAML.exists():
        main_yaml = load_yaml(MAIN_AGENT_YAML)
        for k in ["publish", "agents", "mcpServers"]:
            if k in main_yaml:
                if isinstance(main_yaml[k], dict):
                    if k == "publish":
                        if "tools" in main_yaml[k]:
                            merged["publish"]["tools"].extend(main_yaml[k]["tools"])
                        if "prompts" in main_yaml[k]:
                            merged["publish"]["prompts"].extend(main_yaml[k]["prompts"])
                        if "resources" in main_yaml[k]:
                            merged["publish"]["resources"].extend(main_yaml[k]["resources"])
                        if "resourceTemplates" in main_yaml[k]:
                            merged["publish"]["resourceTemplates"].extend(main_yaml[k]["resourceTemplates"])
                    else:
                        merged[k].update(main_yaml[k])
                elif isinstance(main_yaml[k], list):
                    if k == "publish":
                        merged["publish"]["tools"].extend(main_yaml[k])
                    else:
                        merged[k]["tools"].extend(main_yaml[k])
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_yaml_path = agent_dir / "nanobot.yaml"
        if not agent_yaml_path.exists():
            continue
        agent_yaml = load_yaml(agent_yaml_path)
        if "publish" in agent_yaml:
            if "tools" in agent_yaml["publish"]:
                merged["publish"]["tools"].extend(agent_yaml["publish"]["tools"])
            if "prompts" in agent_yaml["publish"]:
                merged["publish"]["prompts"].extend(agent_yaml["publish"]["prompts"])
            if "resources" in agent_yaml["publish"]:
                merged["publish"]["resources"].extend(agent_yaml["publish"]["resources"])
            if "resourceTemplates" in agent_yaml["publish"]:
                merged["publish"]["resourceTemplates"].extend(agent_yaml["publish"]["resourceTemplates"])
        if "agents" in agent_yaml:
            merged["agents"].update(agent_yaml["agents"])
        if "mcpServers" in agent_yaml:
            adj = adjust_mcp_paths(agent_dir.name, agent_yaml["mcpServers"])
            for k, v in adj.items():
                if v is not None and isinstance(v, dict):
                    merged["mcpServers"][k] = v
    merged["publish"]["tools"] = list(sorted(set(merged["publish"]["tools"])))
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
    merged["publish"]["resources"] = list(sorted(set(merged["publish"].get("resources", []))))
    merged["publish"]["resourceTemplates"] = list(sorted(set(merged["publish"].get("resourceTemplates", []))))
    entrypoint = None
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_yaml_path = agent_dir / "nanobot.yaml"
        if not agent_yaml_path.exists():
            continue
        agent_yaml = load_yaml(agent_yaml_path)
        if "publish" in agent_yaml and "entrypoint" in agent_yaml["publish"]:
            entrypoint = agent_yaml["publish"]["entrypoint"]
    if not entrypoint and MAIN_AGENT_YAML.exists():
        main_yaml = load_yaml(MAIN_AGENT_YAML)
        if "publish" in main_yaml and "entrypoint" in main_yaml["publish"]:
            entrypoint = main_yaml["publish"]["entrypoint"]
    if entrypoint:
        merged["publish"]["entrypoint"] = entrypoint
    with open(OUTPUT_YAML, "w") as f:
        f.write(
            "# DO NOT EDIT: This file is autogenerated by nanobot_template_util.py.\n"
        )
        yaml.dump(merged, f, sort_keys=False)
    print(f"Merged nanobot.yaml written to {OUTPUT_YAML}")

def merge_all_configs():
    return merge_nanobot_yamls()

if __name__ == "__main__":
    merge_nanobot_yamls()
