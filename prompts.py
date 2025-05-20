from fastmcp import FastMCP
import importlib.util
import sys
from pathlib import Path

mcp = FastMCP(name="prompts")

AGENTS_DIR = Path(__file__).parent / "agents"

# Dynamically load prompt.py from each agent and register its tools
for agent_dir in AGENTS_DIR.iterdir():
    prompt_path = agent_dir / "prompt.py"
    if prompt_path.exists():
        spec = importlib.util.spec_from_file_location(f"{agent_dir.name}_prompt", str(prompt_path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        # If the agent's prompt.py defines a register_prompts(mcp) function, call it
        if hasattr(module, "register_prompts"):
            module.register_prompts(mcp)

if __name__ == "__main__":
    mcp.run()
