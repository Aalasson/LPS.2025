
import os
CATALOG_URL = os.getenv("CATALOG_URL", "http://localhost:8001")
CART_URL    = os.getenv("CART_URL",    "http://localhost:8002")
ORDER_URL   = os.getenv("ORDER_URL",   "http://localhost:8003")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://localhost:8004")
RECO_URL    = os.getenv("RECO_URL",    "http://localhost:8005")
SHIPPING_URL= os.getenv("SHIPPING_URL","http://localhost:8006")

DEFAULT_LOCALE   = os.getenv("DEFAULT_LOCALE", "pt-BR")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "BRL")
ALLOWED_PAYMENT_METHODS = set((os.getenv("ALLOWED_PAYMENT_METHODS","card,pix")).split(","))

RECO_STRATEGY = os.getenv("RECO_STRATEGY","content")  # off|content
RECO_ENABLED  = os.getenv("RECO_ENABLED","true").lower()=="true" and RECO_STRATEGY!="off"

CHECKOUT_GUEST   = os.getenv("CHECKOUT_GUEST","true").lower()=="true"
CHECKOUT_ONECLICK= os.getenv("CHECKOUT_ONECLICK","false").lower()=="true"

SHIPPING_ENABLED = os.getenv("SHIPPING_ENABLED","true").lower()=="true"
SHIPPING_MODE    = os.getenv("SHIPPING_MODE","transportadora")  # transportadora|retirada

SERVICES = {
  "catalog": CATALOG_URL,
  "cart": CART_URL,
  "order": ORDER_URL,
  "payment": PAYMENT_URL,
  "recommendation": RECO_URL if RECO_ENABLED else None,
  "shipping": SHIPPING_URL if SHIPPING_ENABLED else None,
}
