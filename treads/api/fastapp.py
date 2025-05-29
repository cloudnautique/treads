from fastapi import FastAPI
from .lifespan import lifespan

App = FastAPI(lifespan=lifespan)