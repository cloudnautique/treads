import sys
from pathlib import Path
import shutil

TEMPLATE_DIR = Path(__file__).parent / "project_template"


def copy_template_dir(src, dst):
    """Recursively copy template directory from src to dst."""
    for item in src.iterdir():
        dest_item = dst / item.name
        if item.is_dir():
            dest_item.mkdir(parents=True, exist_ok=True)
            copy_template_dir(item, dest_item)
        else:
            dest_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, dest_item)


def create_project():
    if len(sys.argv) < 2:
        print("Usage: create_project [PROJECT_NAME]")
        sys.exit(1)
    project = sys.argv[1]
    root = Path(project)
    if not TEMPLATE_DIR.exists():
        print(
            f"Template directory {TEMPLATE_DIR} not found. Please ensure project_template/ exists in the package and is included as package data."
        )
        sys.exit(1)
    copy_template_dir(TEMPLATE_DIR, root)

    dirs = ["agents", "static"]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    print(f"treads project '{project}' scaffolded from {TEMPLATE_DIR}.")


# Use the agents directory in the current working directory (the user's project)
AGENTS_DIR = Path.cwd() / "agents"


def copy_agent_template_dir(src, dst, agent_name):
    """Recursively copy agent template directory from src to dst, substituting {name}."""
    for item in src.iterdir():
        dest_item = dst / item.name
        if item.is_dir():
            dest_item.mkdir(parents=True, exist_ok=True)
            copy_agent_template_dir(item, dest_item, agent_name)
        else:
            dest_item.parent.mkdir(parents=True, exist_ok=True)
            with open(item, "r") as f:
                content = f.read().replace("{name}", agent_name)
            with open(dest_item, "w") as out:
                out.write(content)


def create_agent():
    if len(sys.argv) < 2:
        print("Usage: create_agent [AGENT_NAME]")
        sys.exit(1)
    agent = sys.argv[1]
    agent_dir = AGENTS_DIR / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_template_dir = Path(__file__).parent / "agent_template"
    if not agent_template_dir.exists():
        print(
            f"Agent template directory {agent_template_dir} not found. Please ensure agent_template/ exists in the package and is included as package data."
        )
        sys.exit(1)
    copy_agent_template_dir(agent_template_dir, agent_dir, agent)
    print(f"Agent '{agent}' created in {agent_dir}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create_project":
        sys.argv.pop(1)
        create_project()
    elif len(sys.argv) > 1 and sys.argv[1] == "create_agent":
        sys.argv.pop(1)
        create_agent()
    else:
        print("Usage: tread_manage.py [create_project|create_agent] [NAME]")
        sys.exit(1)
