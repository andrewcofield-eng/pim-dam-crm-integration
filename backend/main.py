from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv
from openai import OpenAI
from orchestrator import ABMSimulationOrchestrator
import os
load_dotenv()
app = FastAPI(title="UrbanThread Marketing API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
async def get_product(sku: str):
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
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "UrbanThread Marketing API", "version": "2.0.0"}
@app.get("/products")
async def list_products():
@app.get("/products")
async def list_products():
    try:
        token = await get_directus_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DIRECTUS_URL}/items/products", headers=headers)
        
        # Get products from Directus
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
    try:
        return await get_product(sku)
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
@app.post("/campaigns/generate")
async def generate_campaign(product_sku: str, target_segment: str):
    try:
        product = await get_product(product_sku)
        product_name = product.get("product_name") or product.get("product_name") or product.get("sku")
        description = product.get("Description") or product.get("short_description") or ""
        tags = product.get("tags", [])
        if isinstance(tags, list):
            tags_str = ", ".join(tags)
        else:
            tags_str = str(tags)
        prompt = (
            "You are a creative marketing strategist for UrbanThread, a fashion brand.\n\n"
            f"Product: {product_name}\n"
            f"Description: {description}\n"
            f"Category: {product.get('category')}\n"
            f"Price: \\n"
            f"Tags: {tags_str}\n"
            f"Target Segment: {target_segment}\n\n"
            "Generate a complete marketing campaign with ALL of the following sections:\n\n"
            "1. CAMPAIGN HEADLINE (max 10 words)\n"
            "2. CAMPAIGN BODY COPY (3-4 sentences, engaging and on-brand)\n"
            "3. CALL TO ACTION (punchy, max 8 words)\n"
            "4. KEY BENEFITS (3 bullet points)\n"
            "5. EMAIL SUBJECT LINE (max 50 characters, high open-rate)\n"
            "6. EMAIL PREVIEW TEXT (max 90 characters)\n"
            "7. EMAIL BODY (3 paragraphs: hook, product story, closing CTA)\n"
            "8. INSTAGRAM AD COPY (max 125 characters, include 3 hashtags)\n"
            "9. GOOGLE AD HEADLINE (max 30 characters)\n"
            "10. GOOGLE AD DESCRIPTION (max 90 characters)\n\n"
            f"Keep tone appropriate for the {target_segment} segment. Be specific to the product, no generic copy."
        )
        message = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a senior creative marketing director specializing in fashion and lifestyle brands."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.75,
            max_tokens=1000
        )
        campaign_text = message.choices[0].message.content
        return {
            "product_sku": product_sku,
            "product_name": product_name,
            "target_segment": target_segment,
            "category": product.get("category"),
            "price": product.get("price"),
            "cloudinary_url": product.get("cloudinary_url"),
            "campaign": campaign_text,
            "ai_model": "gpt-3.5-turbo",
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from abm_routes import router as abm_router
app.include_router(abm_router)
@app.get("/auth/token")
async def get_token():
    token = await get_directus_token()
    return {"token": token}
from campaign_routes import router as campaign_router
app.include_router(campaign_router)

from hubspot_routes import router as hubspot_router
app.include_router(hubspot_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
