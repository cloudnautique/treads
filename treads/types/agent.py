from pydantic import BaseModel

class NanobotAgent(BaseModel):
    name: str
    dir: str
    address: str
