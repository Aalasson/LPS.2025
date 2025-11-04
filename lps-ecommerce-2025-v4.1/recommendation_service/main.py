
from fastapi import FastAPI, HTTPException
from typing import Optional
import os, httpx
from stop_words import get_stop_words
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CATALOG_URL=os.getenv("CATALOG_URL","http://localhost:8001")
app = FastAPI(title="Recommendation Service", version="0.2.1")

catalog=[]; tfidf_matrix=None
vectorizer=TfidfVectorizer(stop_words=get_stop_words("portuguese"))

async def fetch_catalog():
    async with httpx.AsyncClient() as c:
        r=await c.get(f"{CATALOG_URL}/products", timeout=10.0)
        r.raise_for_status()
        return r.json()

def rebuild_index():
    global tfidf_matrix
    corpus=[f"{p['name']} {p['description']} {p['category']}" for p in catalog]
    tfidf_matrix = vectorizer.fit_transform(corpus) if corpus else None

@app.on_event("startup")
async def startup():
    global catalog
    catalog = await fetch_catalog()
    rebuild_index()

@app.get("/")
def root():
    return {"ok": True, "use": "/docs"}

@app.get("/health")
def health():
    return {"ok": True, "size": len(catalog)}

@app.get("/recommendations")
async def recommendations(context:str, item_id: Optional[str]=None, limit:int=12):
    if tfidf_matrix is None or not catalog:
        raise HTTPException(status_code=503, detail="Index not ready")
    if context=="product":
        if not item_id:
            raise HTTPException(status_code=400, detail="item_id required")
        idx=next((i for i,p in enumerate(catalog) if p["sku"]==item_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="item not found")
        sims = cosine_similarity(tfidf_matrix[idx], tfidf_matrix).flatten()
        pairs=sorted([(i,float(s)) for i,s in enumerate(sims) if i!=idx], key=lambda x:x[1], reverse=True)[:limit]
        items=[{"item_id":catalog[i]["sku"],"score":s,"reason":"content_similarity"} for i,s in pairs]
        return {"items":items,"variant":"content_tfidf_v1"}
    tops=sorted(catalog, key=lambda p:p["price"], reverse=True)[:limit]
    return {"items":[{"item_id":p["sku"],"score":0.5,"reason":"fallback_popular"} for p in tops],"variant":"fallback_popular"}
