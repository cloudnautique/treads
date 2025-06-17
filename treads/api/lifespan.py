import subprocess
import signal
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger(__name__)

nanobot_processes = []


def create_lifespan(agents=None):
    agents = agents or []

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global nanobot_processes
        # Startup: launch each agent
        for agent in agents:
            agent_dir = os.path.join("./", agent.dir)
            proc = subprocess.Popen(
                ["nanobot", "run", agent_dir, "--mcp", "--listen-address", agent.address]
            )
            nanobot_processes.append(proc)
        try:
            yield
        finally:
            # Shutdown: stop all agents
            for proc in nanobot_processes:
                proc.send_signal(signal.SIGINT)
                proc.wait()
            nanobot_processes.clear()

    return lifespan