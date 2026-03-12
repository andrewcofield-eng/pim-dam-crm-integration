from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv
from openai import OpenAI

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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "UrbanThread Marketing API"}

@app.get("/products")
async def list_products():
    try:
        token = await get_directus_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DIRECTUS_URL}/items/products",
                headers=headers
            )
        
        return response.json()["data"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{sku}")
async def get_product(sku: str):
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

@app.post("/campaigns/generate")
async def generate_campaign(product_sku: str, target_segment: str):
    try:
        token = await get_directus_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DIRECTUS_URL}/items/products?filter[sku][_eq]={product_sku}",
                headers=headers
            )
        
        products = response.json()["data"]
        if not products:
            raise HTTPException(status_code=404, detail=f"Product {product_sku} not found")
        
        product = products[0]
        
        prompt = f"""You are a creative marketing strategist for UrbanThread, a fashion brand.

Product: {product['sku']} - {product['short_description']}
Category: {product['category']}
Price: \
Target Segment: {target_segment}

Generate a compelling marketing campaign with:
1. Headline (max 10 words)
2. Body copy (2-3 sentences)
3. Call-to-action
4. Key benefits (3 bullets)

Keep it professional and engaging."""
        
        message = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative marketing expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        return {
            "product_sku": product_sku,
            "target_segment": target_segment,
            "campaign": message.choices[0].message.content,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
