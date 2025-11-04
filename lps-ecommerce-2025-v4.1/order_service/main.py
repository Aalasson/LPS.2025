
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models import Order, OrderItem
from db import init_db, get_session
import httpx, os

CATALOG_URL=os.getenv("CATALOG_URL","http://localhost:8001")
CART_URL=os.getenv("CART_URL","http://localhost:8002")
PAYMENT_URL=os.getenv("PAYMENT_URL","http://localhost:8004")

app = FastAPI(title="Order Service", version="0.1.1")

@app.on_event("startup")
def startup():
    init_db()

class CreateOrder(BaseModel):
    session_id:str
    payment_method:str

@app.get("/")
def root():
    return {"ok": True, "use": "/docs"}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/orders")
async def create_order(payload: CreateOrder):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CART_URL}/cart", headers={"X-Session-Id": payload.session_id}, timeout=10.0)
        cart = r.json().get("items", {})
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    items, total = [], 0.0
    async with httpx.AsyncClient() as c:
        for sku, qty in cart.items():
            r = await c.get(f"{CATALOG_URL}/products/{sku}", timeout=10.0)
            if r.status_code!=200:
                raise HTTPException(status_code=400, detail=f"SKU {sku} not found")
            p = r.json()
            price = float(p["price"])
            items.append({"sku":sku,"qty":int(qty),"price":price})
            total += price*int(qty)

    async with httpx.AsyncClient() as c:
        r = await c.post(f"{PAYMENT_URL}/authorize", json={"order_id":"tmp-"+payload.session_id,"amount":total,"method":payload.payment_method}, timeout=10.0)
        auth = r.json()
    if auth.get("status")!="APPROVED":
        raise HTTPException(status_code=402, detail={"payment":auth})

    with get_session() as s:
        order = Order(session_id=payload.session_id, total=round(total,2), status="PAID")
        s.add(order); s.commit(); s.refresh(order)
        for it in items:
            s.add(OrderItem(order_id=order.id, sku=it["sku"], qty=it["qty"], price=it["price"]))
        s.commit()
    return {"order_id": order.id, "status":"PAID", "total":order.total, "items":items}
