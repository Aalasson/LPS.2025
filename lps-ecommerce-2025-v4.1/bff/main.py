
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
import httpx, os, yaml
from pydantic import BaseModel
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import *

app = FastAPI(title="BFF / API Gateway", version="0.4.1")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape())

def session_id_from(request: Request) -> str:
    sid = request.headers.get("X-Session-Id")
    if not sid:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header")
    return sid

@app.get("/")
def root():
    return {"ok": True, "use": "/docs, /status, /config, /storefront"}

@app.get("/health")
def health():
    return {
        "ok": True,
        "ui": {"locale": DEFAULT_LOCALE, "currency": DEFAULT_CURRENCY},
        "checkout": {"guest": CHECKOUT_GUEST, "oneclick": CHECKOUT_ONECLICK},
        "shipping": {"enabled": SHIPPING_ENABLED, "mode": SHIPPING_MODE},
        "payments": sorted(list(ALLOWED_PAYMENT_METHODS)),
        "reco": {"enabled": RECO_ENABLED, "strategy": RECO_STRATEGY},
    }

# Catalog
@app.get("/api/v1/catalog/products")
async def list_products(q: Optional[str] = None):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CATALOG_URL}/products", params={"q": q} if q else None, timeout=10.0)
        return r.json()

@app.get("/api/v1/catalog/products/{sku}")
async def get_product(sku: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CATALOG_URL}/products/{sku}", timeout=10.0)
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="SKU not found")
        return r.json()

# Cart
class CartItem(BaseModel):
    sku: str
    qty: int

@app.get("/api/v1/cart")
async def get_cart(request: Request):
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CART_URL}/cart", headers={"X-Session-Id": sid}, timeout=10.0)
        return r.json()

@app.post("/api/v1/cart/items")
async def add_item(request: Request, item: CartItem):
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{CART_URL}/cart/items", json=item.model_dump(), headers={"X-Session-Id": sid}, timeout=10.0)
        return r.json()

@app.delete("/api/v1/cart/items/{sku}")
async def remove_item(request: Request, sku: str):
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{CART_URL}/cart/items/{sku}", headers={"X-Session-Id": sid}, timeout=10.0)
        return r.json()

# Checkout
class CheckoutPayload(BaseModel):
    payment_method: str

@app.post("/api/v1/checkout/start")
async def checkout_start(request: Request, payload: CheckoutPayload):
    if payload.payment_method not in ALLOWED_PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail=f"Payment method '{payload.payment_method}' not allowed.")
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{ORDER_URL}/orders", json={"session_id": sid, "payment_method": payload.payment_method}, timeout=30.0)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.json())
        return r.json()

# Shipping
@app.get("/api/v1/shipping/quote")
async def shipping_quote(request: Request, zip: str):
    if not SHIPPING_ENABLED:
        raise HTTPException(status_code=501, detail="Shipping disabled")
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CART_URL}/cart", headers={"X-Session-Id": sid}, timeout=10.0)
        items = [{"sku": k, "qty": v} for k, v in r.json().get("items", {}).items()]
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    payload = {"zip": zip, "mode": SHIPPING_MODE, "items": items}
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{SHIPPING_URL}/quote", json=payload, timeout=10.0)
        return r.json()

# Recommendations
@app.get("/api/v1/recommendations")
async def recommendations(context: str, item_id: Optional[str] = None, limit: int = 12):
    if not RECO_ENABLED:
        raise HTTPException(status_code=501, detail="Recommendations disabled")
    params = {"context": context, "limit": limit}
    if item_id:
        params["item_id"] = item_id
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{RECO_URL}/recommendations", params=params, timeout=10.0)
        return r.json()

# Status helpers
async def fetch_health(name: str, url: Optional[str]) -> Dict[str, Any]:
    if not url:
        return {"name": name, "enabled": False, "ok": False, "detail": "disabled"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{url}/health", timeout=5.0)
            return {"name": name, "enabled": True, "ok": r.status_code == 200, "data": r.json()}
    except Exception as e:
        return {"name": name, "enabled": True, "ok": False, "error": str(e)}

@app.get("/api/v1/status")
async def status_json():
    results = {}
    for name, url in SERVICES.items():
        results[name] = await fetch_health(name, url)
    results["config"] = health()
    return results

@app.get("/status", response_class=HTMLResponse)
async def status_html():
    tmpl = env.get_template("status.html")
    statuses = []
    for name, url in SERVICES.items():
        statuses.append(await fetch_health(name, url))
    return tmpl.render(statuses=statuses, config=health())

@app.get("/config", response_class=HTMLResponse)
def config_page():
    tmpl = env.get_template("config.html")
    defaults = {"locale": DEFAULT_LOCALE, "currency": DEFAULT_CURRENCY, "payments": sorted(list(ALLOWED_PAYMENT_METHODS)),
                "reco_strategy": "content" if RECO_ENABLED else "off", "checkout_guest": CHECKOUT_GUEST,
                "checkout_oneclick": CHECKOUT_ONECLICK, "shipping_enabled": SHIPPING_ENABLED, "shipping_mode": SHIPPING_MODE}
    return tmpl.render(defaults=defaults)

@app.post("/config", response_class=PlainTextResponse)
def generate_features_yaml(locale: str = Form("pt-BR"), currency: str = Form("BRL"), payments: str = Form("card,pix"),
                           reco_strategy: str = Form("content"), checkout_guest: str = Form("true"),
                           checkout_oneclick: str = Form("false"), shipping_enabled: str = Form("true"),
                           shipping_mode: str = Form("transportadora")):
    cfg = {"ui": {"locale": locale, "currency": currency},
           "checkout": {"guest": checkout_guest.lower() == "true", "oneclick": checkout_oneclick.lower() == "true"},
           "shipping": {"enabled": shipping_enabled.lower() == "true", "mode": shipping_mode},
           "payments": {"methods": [p.strip() for p in payments.split(",") if p.strip()]},
           "recommendation": {"strategy": reco_strategy}}
    return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)

@app.get("/storefront", response_class=HTMLResponse)
async def storefront_html():
    tmpl = env.get_template("storefront.html")
    statuses = []
    for name, url in SERVICES.items():
        statuses.append(await fetch_health(name, url))
    return tmpl.render(config=health(), statuses=statuses)
