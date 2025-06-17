from fastapi import FastAPI
from .lifespan import create_lifespan
from treads.api.routers import TreadRouter


def load_default_app_config(agents=None):
    lifespan = create_lifespan(agents=agents)
    app = FastAPI(lifespan=lifespan)
    app.include_router(TreadRouter)

    return app