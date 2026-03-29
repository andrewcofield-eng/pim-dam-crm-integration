from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv
from openai import OpenAI
from orchestrator import ABMSimulationOrchestrator

load_dotenv()

app = FastAPI(title="UrbanThread Marketing API", version="1.0.0", debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://localhost:8055")
DIRECTUS_EMAIL = os.getenv("DIRECTUS_EMAIL", "admin@portfolio.com")
DIRECTUS_PASSWORD = os.getenv("DIRECTUS_PASSWORD", "admin123")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

async def get_directus_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DIRECTUS_URL}/auth/login",
            json={"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD}
        )
        return response.json()["data"]["access_token"]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "UrbanThread Marketing API", "version": "2.0.0"}

@app.get("/products")
async def list_products():
    try:
        token = await get_directus_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DIRECTUS_URL}/items/products", headers=headers)
        
        products = response.json()["data"]
        
        # FIX: Override cloudinary_url for products 11-30 with correct JPG URLs
        url_map = {
            "TOP-003": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236179/TOP-003_fsomai.jpg",
            "TOP-004": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774234835/TOP-004_pu7ydv.jpg",
            "HOD-003": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236178/HOD-003_vm9yux.jpg",
            "HOD-004": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774234835/HOD-004_t5dole.jpg",
            "DNM-003": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774238034/DNM-003_addc2l.jpg",
            "DNM-004": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236526/DNM-004_zfbmoo.jpg",
            "OUT-003": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236179/OUT-003_mrv2b1.jpg",
            "OUT-004": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236179/OUT-004_yhklka.jpg",
            "ACC-003": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236169/ACC-003_ymymuu.jpg",
            "ACC-004": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/ACC-004_kidq0y.jpg",
            "ACC-005": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236169/ACC-005_tsrzyb.jpg",
            "KNIT-001": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/KNIT-001_yjajnw.jpg",
            "KNIT-002": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/KNIT-002_ulqvek.jpg",
            "SHORT-001": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/SHORT-001_n5cklw.jpg",
            "SHORT-002": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236526/SHORT-002_mjinid.jpg",
            "SHIRT-001": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/SHIRT-001_ghcvts.jpg",
            "SHIRT-002": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/SHIRT-002_suuyfo.jpg",
            "SWIM-001": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236526/SWIM-001_hoqsjv.jpg",
            "SOCK-001": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/SOCK-001_wghtxb.jpg",
            "UNDER-001": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/UNDER-001_rx940w.jpg",
        }
        
        for product in products:
            sku = product.get("sku", "")
            if sku in url_map:
                product["cloudinary_url"] = url_map[sku]
        
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{sku}")
async def get_product_endpoint(sku: str):
    try:
        token = await get_directus_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DIRECTUS_URL}/items/products?filter[sku][_eq]={sku}",
                headers=headers
            )
        products = response.json()["data"]
        if not products:
            raise HTTPException(status_code=404, detail=f"Product {sku} not found")
        return products[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/customers")
async def list_customers():
    return [
        {"firstname": "Sarah", "lastname": "Chen", "segment": "Everyday Basics"},
        {"firstname": "Lisa", "lastname": "Thompson", "segment": "Premium Casual"},
        {"firstname": "Alex", "lastname": "Martinez", "segment": "Streetwear"},
        {"firstname": "Riley", "lastname": "Garcia", "segment": "Active Lifestyle"},
    ]

# ─── Routers ──────────────────────────────────────────────────────────────────
from abm_routes import router as abm_router
app.include_router(abm_router)

@app.get("/auth/token")
async def get_token():
    token = await get_directus_token()
    return {"token": token}

from campaign_routes import router as campaign_router
app.include_router(campaign_router)   # handles POST /ai-campaigns/generate

from hubspot_routes import router as hubspot_router
app.include_router(hubspot_router)

from campaign_html_routes import router as html_campaign_router
app.include_router(html_campaign_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

