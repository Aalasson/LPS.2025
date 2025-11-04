
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

app = FastAPI(title="Payment Service", version="0.1.1")

class AuthRequest(BaseModel):
    order_id: str
    amount: float
    method: Literal["card","pix","boleto","wallet"]

@app.get("/")
def root():
    return {"ok": True, "use": "/docs"}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/authorize")
def authorize(req: AuthRequest):
    approved, reason = True, "approved"
    if req.method=="card" and req.amount>1500:
        approved, reason = False, "limit_exceeded"
    if req.method=="boleto" and req.amount<20:
        approved, reason = False, "min_amount_not_met"
    return {"status":"APPROVED" if approved else "DECLINED", "reason": reason, "provider":"demo-psp"}
