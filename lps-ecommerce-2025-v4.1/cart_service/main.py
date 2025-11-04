
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI(title="Cart Service", version="0.1.1")
CARTS: Dict[str, Dict[str, int]] = {}

def sid(req:Request)->str:
    s=req.headers.get("X-Session-Id")
    if not s:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header")
    return s

class Item(BaseModel):
    sku:str
    qty:int

@app.get("/")
def root():
    return {"ok": True, "use": "/docs"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/cart")
def get_cart(request:Request):
    s=sid(request)
    return {"session_id": s, "items": CARTS.get(s,{})}

@app.post("/cart/items")
def add_item(request:Request, item:Item):
    s=sid(request)
    cart=CARTS.setdefault(s,{})
    cart[item.sku]=cart.get(item.sku,0)+int(item.qty)
    return {"session_id": s, "items": cart}

@app.delete("/cart/items/{sku}")
def remove_item(request:Request, sku:str):
    s=sid(request)
    cart=CARTS.setdefault(s,{})
    if sku in cart:
        del cart[sku]
    return {"session_id": s, "items": cart}
