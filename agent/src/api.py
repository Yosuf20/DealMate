# agent/src/api.py
from fastapi import FastAPI
from pydantic import BaseModel
from src.supervisor import run_supervisor  # adjust to your actual function name

app = FastAPI()

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
def search(req: SearchRequest):
    return run_supervisor(req.query)