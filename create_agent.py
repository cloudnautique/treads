import sys
from pathlib import Path

AGENTS_DIR = Path(__file__).parent / "agents"

NANOBOT_YAML_TEMPLATE = """publish:
  tools: [{name}]

agents:
  {name}:
    model: gpt-4.1
    instructions: |-
      You are a {name} agent. Describe what you do here.
    tools: [{name}_tools]

mcpServers:
  {name}_tools:
    command: "uv"
    args:
    - "run"
    - "tools.py"
"""

TOOLS_PY_TEMPLATE = """from fastmcp import FastMCP

mcp = FastMCP(name="{name}")

@mcp.tool()
def {name}(text: str) -> str:
    '''Describe what this tool does.'''
    return f"{name} tool called with: {{text}} (stub)"

if __name__ == "__main__":
    mcp.run()
"""

PROMPT_PY_TEMPLATE = """from fastmcp import FastMCP

def register_prompts(mcp: FastMCP):
    @mcp.prompt()
    def {name}_prompt(text: str) -> str:
        '''Describe what this prompt does.'''
        return f"Prompt for {name}: {{text}} (stub)"
"""

def main():
    if len(sys.argv) < 2:
        print("Usage: create_agent.py [AGENT_NAME]")
        sys.exit(1)
    agent = sys.argv[1]
    agent_dir = AGENTS_DIR / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    # nanobot.yaml
    with open(agent_dir / "nanobot.yaml", "w") as f:
        f.write(NANOBOT_YAML_TEMPLATE.format(name=agent))
    # tools.py
    with open(agent_dir / "tools.py", "w") as f:
        f.write(TOOLS_PY_TEMPLATE.format(name=agent))
    # prompt.py
    with open(agent_dir / "prompt.py", "w") as f:
        f.write(PROMPT_PY_TEMPLATE.format(name=agent))
    print(f"Agent '{agent}' created in {agent_dir}")

if __name__ == "__main__":
    main()
