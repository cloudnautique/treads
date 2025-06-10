import sys
from pathlib import Path
import shutil
import subprocess
import os

TEMPLATE_DIR = Path(__file__).parent / "project_template"


def copy_template_dir(src, dst):
    """Recursively copy template directory from src to dst."""
    for item in src.iterdir():
        # Skip files we don't want to copy
        if should_skip_file(item):
            continue
            
        dest_item = dst / item.name
        if item.is_dir():
            dest_item.mkdir(parents=True, exist_ok=True)
            copy_template_dir(item, dest_item)
        else:
            try:
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(item, dest_item)
            except Exception as e:
                print(f"Warning: Failed to copy {item} to {dest_item}: {e}")


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
    # Correctly create the 'app' agent as a child of the project directory
    prev_cwd = Path.cwd()
    try:
        os.chdir(root)
        print(f"Creating agent 'app' in {root}")
        print(f"Current working directory: {os.getcwd()}")
        create_agent_with_name("app")
    finally:
        os.chdir(prev_cwd)
    print(f"treads project '{project}' scaffolded from {TEMPLATE_DIR}.")


def create_agent_with_name(agent_name):
    agent_dir = Path.cwd() / "agents" / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    # Use the unified agent template for all agents
    agent_template_dir = Path(__file__).parent / "agent_template"
    if not agent_template_dir.exists():
        print(
            f"Agent template directory {agent_template_dir} not found. Please ensure it exists in the package and is included as package data."
        )
        sys.exit(1)
    copy_agent_template_dir(agent_template_dir, agent_dir, agent_name)
    print(f"Agent '{agent_name}' created in {agent_dir}")


# Use the agents directory in the current working directory (the user's project)
AGENTS_DIR = Path.cwd() / "agents"


def should_skip_file(path):
    """Check if a file or directory should be skipped during copying."""
    name = path.name
    
    # Skip directories
    if path.is_dir():
        return name == "__pycache__" or name == ".git" or name == ".venv" or name == "venv"
        
    # Skip files
    return (
        name.endswith(".pyc") or
        name.endswith(".pyo") or
        name.endswith(".pyd") or
        name.startswith(".DS_Store") or
        name.endswith("~") or  # Editor backup files
        name.endswith(".swp")  # Vim swap files
    )

def is_binary_file(file_path):
    """Check if file is binary by reading a chunk and looking for null bytes or invalid UTF-8 characters."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)  # Read a chunk to check encoding
        return False
    except UnicodeDecodeError:
        return True

def copy_agent_template_dir(src, dst, agent_name):
    """Recursively copy agent template directory from src to dst, substituting {name}. Also copy 'templates' dir if present."""
    for item in src.iterdir():
        # Skip files we don't want to copy
        if should_skip_file(item):
            continue
            
        # Handle filename substitution - replace {name} in filenames
        dest_name = item.name.replace("{name}", agent_name)
        dest_item = dst / dest_name
        
        if item.is_dir():
            dest_item.mkdir(parents=True, exist_ok=True)
            # If this is a 'templates' directory, copy all its contents recursively with filename substitution
            if item.name == "templates":
                try:
                    # Create a custom copytree function that uses our file skipping logic and filename substitution
                    def custom_copy(src, dst, symlinks=False, ignore=None):
                        os.makedirs(dst, exist_ok=True)
                        for item in os.listdir(src):
                            s = os.path.join(src, item)
                            if should_skip_file(Path(s)):
                                continue
                                
                            # Apply filename substitution
                            dest_filename = item.replace("{name}", agent_name)
                            d = os.path.join(dst, dest_filename)
                            if os.path.isdir(s):
                                custom_copy(s, d, symlinks, ignore)
                            else:
                                # Copy file with content substitution
                                if is_binary_file(Path(s)):
                                    shutil.copy2(s, d)
                                else:
                                    try:
                                        with open(s, "r", encoding="utf-8") as f:
                                            content = f.read().replace("{name}", agent_name)
                                        with open(d, "w", encoding="utf-8") as out:
                                            out.write(content)
                                        # Copy file metadata
                                        shutil.copystat(s, d)
                                    except Exception as e:
                                        print(f"Warning: Could not process {s}, copying directly: {e}")
                                        shutil.copy2(s, d)
                    
                    custom_copy(str(item), str(dest_item))
                except Exception as e:
                    print(f"Warning: Error copying template directory {item}: {e}")
                    # Try to continue with a file-by-file copy as fallback
                    for template_item in item.iterdir():
                        if should_skip_file(template_item):
                            continue
                        try:
                            dest_template_name = template_item.name.replace("{name}", agent_name)
                            dest_template = dest_item / dest_template_name
                            if template_item.is_dir():
                                shutil.copytree(template_item, dest_template, dirs_exist_ok=True)
                            else:
                                if is_binary_file(template_item):
                                    shutil.copyfile(template_item, dest_template)
                                else:
                                    try:
                                        with open(template_item, "r", encoding="utf-8") as f:
                                            content = f.read().replace("{name}", agent_name)
                                        with open(dest_template, "w", encoding="utf-8") as out:
                                            out.write(content)
                                    except Exception as inner_e:
                                        print(f"Warning: Could not process {template_item}, copying directly: {inner_e}")
                                        shutil.copyfile(template_item, dest_template)
                        except Exception as inner_e:
                            print(f"Warning: Failed to copy template file {template_item}: {inner_e}")
            else:
                copy_agent_template_dir(item, dest_item, agent_name)
        else:
            dest_item.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file is binary
            if is_binary_file(item):
                # Copy binary files directly without text processing
                shutil.copyfile(item, dest_item)
            else:
                # Process text files with replacement
                try:
                    with open(item, "r", encoding="utf-8") as f:
                        content = f.read().replace("{name}", agent_name)
                    with open(dest_item, "w", encoding="utf-8") as out:
                        out.write(content)
                except Exception as e:
                    # Fallback to direct copy if any error occurs
                    print(f"Warning: Could not process {item}, copying directly: {e}")
                    shutil.copyfile(item, dest_item)


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


def dev():
    """Run uvicorn app:app --reload for development server."""
    subprocess.run(["uvicorn", "app:app", "--reload"])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create_project":
        sys.argv.pop(1)
        create_project()
    elif len(sys.argv) > 1 and sys.argv[1] == "create_agent":
        sys.argv.pop(1)
        create_agent()
    elif len(sys.argv) > 1 and sys.argv[1] == "dev":
        sys.argv.pop(1)
        dev()
    else:
        print("Usage: tread_manage.py [create_project|create_agent|dev] [NAME]")
        sys.exit(1)
