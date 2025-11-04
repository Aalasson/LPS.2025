from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import HTMLResponse
import httpx
import os
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

# importa os valores padrão do ambiente
from config import (
    CATALOG_URL,
    CART_URL,
    ORDER_URL,
    PAYMENT_URL,
    RECO_URL,
    SHIPPING_URL,
    DEFAULT_LOCALE,
    DEFAULT_CURRENCY,
    ALLOWED_PAYMENT_METHODS,
    RECO_STRATEGY,
    CHECKOUT_GUEST,
    CHECKOUT_ONECLICK,
    SHIPPING_ENABLED,
    SHIPPING_MODE,
    SERVICES,
)

app = FastAPI(title="BFF / API Gateway", version="0.5.1")

# ---------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape()
)

# ---------------------------------------------------------------------
# Configuração em memória (runtime)
# ---------------------------------------------------------------------
runtime_config = {
    "ui": {
        "locale": DEFAULT_LOCALE,
        "currency": DEFAULT_CURRENCY,
    },
    "checkout": {
        "guest": CHECKOUT_GUEST,
        "oneclick": CHECKOUT_ONECLICK,
    },
    "shipping": {
        "enabled": SHIPPING_ENABLED,
        "mode": SHIPPING_MODE,
    },
    "payments": {
        "methods": sorted(list(ALLOWED_PAYMENT_METHODS)),
    },
    "recommendation": {
        "strategy": RECO_STRATEGY,  # "off" | "content"
    },
}


def current_config() -> dict:
    """Devolve sempre a configuração que está valendo agora."""
    return runtime_config


def session_id_from(request: Request) -> str:
    sid = request.headers.get("X-Session-Id")
    if not sid:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header")
    return sid


# ---------------------------------------------------------------------
# Rotas básicas
# ---------------------------------------------------------------------
@app.get("/")
def root():
    return {"ok": True, "use": "/docs, /status, /config, /storefront"}


@app.get("/health")
def health():
    cfg = current_config()
    return {
        "ok": True,
        "ui": cfg["ui"],
        "checkout": cfg["checkout"],
        "shipping": cfg["shipping"],
        "payments": cfg["payments"]["methods"],
        "reco": {
            "enabled": cfg["recommendation"]["strategy"] != "off",
            "strategy": cfg["recommendation"]["strategy"],
        },
    }


# ---------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------
@app.get("/api/v1/catalog/products")
async def list_products(q: Optional[str] = None):
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{CATALOG_URL}/products",
            params={"q": q} if q else None,
            timeout=10.0,
        )
        return r.json()


@app.get("/api/v1/catalog/products/{sku}")
async def get_product(sku: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CATALOG_URL}/products/{sku}", timeout=10.0)
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="SKU not found")
        return r.json()


# ---------------------------------------------------------------------
# Carrinho
# ---------------------------------------------------------------------
from pydantic import BaseModel


class CartItem(BaseModel):
    sku: str
    qty: int


@app.get("/api/v1/cart")
async def get_cart(request: Request):
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{CART_URL}/cart",
            headers={"X-Session-Id": sid},
            timeout=10.0,
        )
        return r.json()


@app.post("/api/v1/cart/items")
async def add_item(request: Request, item: CartItem):
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{CART_URL}/cart/items",
            json=item.model_dump(),
            headers={"X-Session-Id": sid},
            timeout=10.0,
        )
        return r.json()


@app.delete("/api/v1/cart/items/{sku}")
async def remove_item(request: Request, sku: str):
    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.delete(
            f"{CART_URL}/cart/items/{sku}",
            headers={"X-Session-Id": sid},
            timeout=10.0,
        )
        return r.json()


# ---------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------
class CheckoutPayload(BaseModel):
    payment_method: str


@app.post("/api/v1/checkout/start")
async def checkout_start(request: Request, payload: CheckoutPayload):
    cfg = current_config()
    allowed = set(cfg["payments"]["methods"])
    if payload.payment_method not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Payment method '{payload.payment_method}' not allowed.",
        )

    sid = session_id_from(request)
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{ORDER_URL}/orders",
            json={"session_id": sid, "payment_method": payload.payment_method},
            timeout=30.0,
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.json())
        return r.json()


# ---------------------------------------------------------------------
# Frete
# ---------------------------------------------------------------------
@app.get("/api/v1/shipping/quote")
async def shipping_quote(request: Request, zip: str):
    cfg = current_config()
    if not cfg["shipping"]["enabled"]:
        raise HTTPException(status_code=501, detail="Shipping disabled")

    sid = session_id_from(request)

    # pega carrinho primeiro
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{CART_URL}/cart",
            headers={"X-Session-Id": sid},
            timeout=10.0,
        )
        items = [
            {"sku": k, "qty": v}
            for k, v in r.json().get("items", {}).items()
        ]

    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    payload = {
        "zip": zip,
        "mode": cfg["shipping"]["mode"],
        "items": items,
    }

    async with httpx.AsyncClient() as c:
        r = await c.post(f"{SHIPPING_URL}/quote", json=payload, timeout=10.0)
        return r.json()


# ---------------------------------------------------------------------
# Recomendações
# ---------------------------------------------------------------------
@app.get("/api/v1/recommendations")
async def recommendations(context: str, item_id: Optional[str] = None, limit: int = 12):
    cfg = current_config()
    if cfg["recommendation"]["strategy"] == "off":
        raise HTTPException(status_code=501, detail="Recommendations disabled")

    params = {"context": context, "limit": limit}
    if item_id:
        params["item_id"] = item_id

    async with httpx.AsyncClient() as c:
        r = await c.get(f"{RECO_URL}/recommendations", params=params, timeout=10.0)
        return r.json()


# ---------------------------------------------------------------------
# Status (JSON + HTML)
# ---------------------------------------------------------------------
async def fetch_health(name: str, url: Optional[str]) -> Dict[str, Any]:
    if not url:
        return {"name": name, "enabled": False, "ok": False, "detail": "disabled"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{url}/health", timeout=5.0)
            return {
                "name": name,
                "enabled": True,
                "ok": r.status_code == 200,
                "data": r.json(),
            }
    except Exception as e:
        return {"name": name, "enabled": True, "ok": False, "error": str(e)}


@app.get("/api/v1/status")
async def status_json():
    results = {}
    for name, url in SERVICES.items():
        results[name] = await fetch_health(name, url)
    # injeta a config atual (runtime) no mesmo JSON
    results["config"] = health()
    return results


@app.get("/status", response_class=HTMLResponse)
async def status_html():
    tmpl = env.get_template("status.html")
    statuses = []
    for name, url in SERVICES.items():
        statuses.append(await fetch_health(name, url))
    return tmpl.render(statuses=statuses, config=health())


# ---------------------------------------------------------------------
# Tela de configuração (HTML) + endpoint que aplica
# ---------------------------------------------------------------------
@app.get("/config", response_class=HTMLResponse)
def config_page():
    tmpl = env.get_template("config.html")
    return tmpl.render()


@app.post("/config/apply")
def apply_config(payload: dict = Body(...)):
    """
    Recebe JSON da tela /config e aplica na config em memória.
    """
    # normaliza shipping
    shipping = payload.get("shipping", {})
    if not shipping.get("enabled", True):
        shipping["mode"] = "transportadora"
    payload["shipping"] = shipping

    # normaliza pagamentos
    payments = payload.get("payments", {})
    methods = payments.get("methods") or []
    if isinstance(methods, str):
        methods = [m.strip() for m in methods.split(",") if m.strip()]
    payments["methods"] = methods
    payload["payments"] = payments

    # aplica
    runtime_config.update(payload)
    return {"ok": True, "applied": runtime_config}


# ---------------------------------------------------------------------
# Storefront (frontend)
# ---------------------------------------------------------------------
@app.get("/storefront", response_class=HTMLResponse)
async def storefront_html():
    tmpl = env.get_template("storefront.html")
    return tmpl.render()
