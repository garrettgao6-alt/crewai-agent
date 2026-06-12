from fastapi import FastAPI
from pydantic import BaseModel

import intelligent_gateway


app = FastAPI()


class AnalyzeRequest(BaseModel):
    query: str


class AnalyzeResponse(BaseModel):
    category: str
    confidence: float
    result: str
    version: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    result = intelligent_gateway.run_gateway_v1(request.query)
    return AnalyzeResponse(**result)
