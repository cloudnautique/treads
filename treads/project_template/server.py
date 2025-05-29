from treads.api.fastapp import App
from treads.api.routers import MCPRouter, TreadRouter, get_ui_resource

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


def create_app():
    app = App  # App is already an instance from fastapp.py
    app.include_router(MCPRouter)
    app.include_router(TreadRouter)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    return app

app = create_app()

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    # Serve the base.html template with minimal context
    return await get_ui_resource(dict({"uri": "ui://app/base"}))