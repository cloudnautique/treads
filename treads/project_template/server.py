from treads.api.fastapp import App
from treads.api.routers import MCPRouter, TreadRouter, get_ui_resource
from treads.config import discover_and_load_agent_configs

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


def create_app():
    # Discover and load all agent configurations
    agent_configs = discover_and_load_agent_configs()
    
    app = App  # App is already an instance from fastapp.py
    app.include_router(MCPRouter)
    app.include_router(TreadRouter)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Store agent configs for potential use in routes
    app.state.agent_configs = agent_configs
    
    return app

app = create_app()

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    # Serve the base.html template with minimal context
    return await get_ui_resource(dict({"uri": "ui://app/base"}))