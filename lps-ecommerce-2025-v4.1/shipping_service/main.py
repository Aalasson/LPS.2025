
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Literal
import httpx, os

CATALOG_URL=os.getenv("CATALOG_URL","http://localhost:8001")
app = FastAPI(title="Shipping Service", version="0.1.1")

class Item(BaseModel):
    sku:str
    qty:int

class QuoteRequest(BaseModel):
    zip:str
    mode:Literal["transportadora","retirada"]
    items: List[Item]

@app.get("/")
def root():
    return {"ok": True, "use": "/docs"}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/quote")
async def quote(req: QuoteRequest):
    if req.mode=="retirada":
        return {"mode":"retirada","cost":0.0,"eta_days":0,"carrier":"retire_na_loja"}
    total=0.0
    async with httpx.AsyncClient() as c:
        for it in req.items:
            r=await c.get(f"{CATALOG_URL}/products/{it.sku}", timeout=10.0)
            if r.status_code!=200:
                raise HTTPException(status_code=400, detail=f"SKU {it.sku} not found")
            p=r.json()
            total += float(p["price"]) * int(it.qty)
    base=14.90; variable=total*0.06; eta = 3 if req.zip.startswith(tuple("0123")) else 7
    return {"mode":"transportadora","cost":round(base+variable,2),"eta_days":eta,"carrier":"demo-express"}
