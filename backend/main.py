from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from orchestrator.orchestrator_agent import create_orchestrator

app = FastAPI()
orchestrator = create_orchestrator()

class Mission(BaseModel):
    mission: str
    vertical: str | None = None
    constraints: dict
    kpis: dict
    time_horizon: dict

@app.post("/run-mission")
async def run_mission(m: Mission):
    payload = m.dict()
    # You could validate against your JSON schema here...
    result = await orchestrator.run_mission(payload)
    return {"status":"ok","result":result}
