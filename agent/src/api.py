# agent/src/api.py
from fastapi import FastAPI
from pydantic import BaseModel
from agent.src.supervisor import run_dealsetu

app = FastAPI()

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
def search(req: SearchRequest):
    return run_dealsetu(req.query)