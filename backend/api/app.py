from fastapi import FastAPI
from backend.fixtures import synthetic_problem
from backend.scheduler.deployment_solver import solve
from backend.scheduler.validation import validate

app=FastAPI(title="Patrol Scheduler",version="0.1.0")
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/demo/schedule")
def demo_schedule():
    problem=synthetic_problem(); result=solve(problem); payload=result.to_dict(); payload["validation"]=validate(problem,result); return payload
