import subprocess
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .nanobot_template_util import merge_all_configs

nanobot_process = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global nanobot_process
    # Startup logic

    merge_all_configs()
    if nanobot_process is None:
        nanobot_process = subprocess.Popen(
            ["nanobot", "run", ".", "--mcp", "--listen-address", "127.0.0.1:8099"]
        )
    try:
        yield
    finally:
        # Shutdown logic
        if nanobot_process is not None:
            nanobot_process.send_signal(signal.SIGINT)
            nanobot_process.wait()
            nanobot_process = None