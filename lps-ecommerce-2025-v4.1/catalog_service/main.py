
from fastapi import FastAPI, HTTPException
from typing import Optional, List
from sqlmodel import select
from models import Product
from db import init_db, get_session
import json, os

app = FastAPI(title="Catalog Service", version="0.1.1")

@app.on_event("startup")
def startup():
    init_db()
    with get_session() as s:
        items = s.exec(select(Product)).all()
        if not items:
            data = json.load(open(os.path.join(os.path.dirname(__file__),"data.json"),"r",encoding="utf-8"))
            for p in data:
                s.add(Product(**p))
            s.commit()

@app.get("/")
def root():
    return {"ok": True, "use": "/docs"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/products")
def list_products(q: Optional[str] = None) -> List[Product]:
    with get_session() as s:
        items = s.exec(select(Product)).all()
        if q:
            ql = q.lower()
            items = [p for p in items if ql in p.name.lower() or ql in p.description.lower() or ql in p.category.lower()]
        return items

@app.get("/products/{sku}")
def get_product(sku: str) -> Product:
    with get_session() as s:
        p = s.get(Product, sku)
        if not p:
            raise HTTPException(status_code=404, detail="Product not found")
        return p
