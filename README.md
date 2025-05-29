# treads

`treads` is a Python framework for building LLM applications with MCP and OpenAI, inspired by Rails/Django.

## Prerequisite: Nanobot MCP Server

Before using treads, you need to install and run a Nanobot MCP server. Follow the instructions in the [nanobot-ai/nanobot README](https://github.com/nanobot-ai/nanobot#readme) to install and start Nanobot.

## Installation (with [uv](https://astral.sh/uv/))

You can use [uv](https://astral.sh/uv/) for fast dependency management and running Python projects. If you don't have uv installed, you can install it with:

```zsh
curl -Ls https://astral.sh/uv/install.sh | sh
```

Then, install treads and its dependencies directly from the GitHub repository:

```zsh
uv pip install git+https://github.com/cloudnautique/treads.git
```

## Quickstart

1. **Create a new project:**

   ```zsh
   uv pip install treads  # (if not already installed)
   uv run -m treads.tread_manage create_project foo
   cd foo
   ```

2. **Set your OpenAI API key:**

   ```zsh
   export OPENAI_API_KEY="sk-..."
   ```

3. **Run the server with uv:**

   ```zsh
   uv run uvicorn server:app --reload
   ```

   Or, for hot-reloading during development:

   ```zsh
   uvicorn server:app --reload
   ```

4. **Open your browser:**

   Go to [http://localhost:8000/](http://localhost:8000/) to see the default chat/tools view.

## Environment Variables

Set these as needed for your environment:

```zsh
export NANOBOT_MCP_URL="http://localhost:8099/mcp"
export OPENAI_MODEL="gpt-4o"
export OPENAI_API_KEY="sk-..."
```

## Features

- Connects to MCP servers (e.g., Nanobot) using FastMCP 2.0
- Provides customizable Views for chat, prompts, and resources
- Integrates with OpenAI for chat and tool calling
- FastAPI-based web server with extensible endpoints

## Next Steps

- Implement chat POST endpoint with OpenAI integration
- Add customizable views for MCP prompts/resources
- Add configuration and app scaffolding tools
