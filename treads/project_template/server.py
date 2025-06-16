import logging 

from treads.api.fastapp import App
from treads.api.routers import TreadRouter
from treads.api.helper import fetch_and_render_ui_resource

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def create_app():
    app = App  # App is already an instance from fastapp.py
    app.include_router(TreadRouter)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    return app

app = create_app()

@app.get("/", response_class=HTMLResponse)
async def chat_view(request: Request):
    # Serve the base.html template with minimal context
    return await fetch_and_render_ui_resource("ui://app/base.html")