# treads

A Python framework for building LLM applications with MCP and OpenAI, inspired by Rails/Django.

## Features
- Connects to MCP servers (e.g., Nanobot) using FastMCP 2.0
- Provides customizable Views for chat, prompts, and resources
- Integrates with OpenAI for chat and tool calling
- FastAPI-based web server with extensible endpoints

## Quickstart

1. Install dependencies:

```zsh
pip install fastapi fastmcp uvicorn
```

2. Set environment variables as needed:

```zsh
export NANOBOT_MCP_URL="http://localhost:8099/mcp"
export OPENAI_MODEL="gpt-4o"
export OPENAI_API_KEY="sk-..."
```

3. Run the server:

```zsh
uvicorn app:app --reload
```

4. Open [http://localhost:8000/](http://localhost:8000/) to see the default chat/tools view.

## Next Steps
- Implement chat POST endpoint with OpenAI integration
- Add customizable views for MCP prompts/resources
- Add configuration and app scaffolding tools
