# backend/app/routers/printful_mockup_routes.py

import os
import httpx
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

router = APIRouter(prefix="/printful-mockups", tags=["Printful Mockups"])

PRINTFUL_API_KEY = os.getenv("PRINTFUL_API_KEY")
PRINTFUL_BASE    = "https://api.printful.com"

# ── SKU → Printful Product + Variant IDs ──────────────────────────────────────
# variant_id = a specific color/size combo on Printful
# placement  = where the design goes (e.g., "front", "back", "embroidery_front")
SKU_TEMPLATE_MAP = {
    "TOP-001": {"product_id": 71,  "variant_id": 4011, "placement": "front"},
    "TOP-002": {"product_id": 87,  "variant_id": 4984, "placement": "front"},
    "TOP-003": {"product_id": 380, "variant_id": 9969, "placement": "front"},
    "TOP-004": {"product_id": 392, "variant_id": 10138,"placement": "front"},
    "HOD-001": {"product_id": 146, "variant_id": 7762, "placement": "front"},
    "HOD-002": {"product_id": 503, "variant_id": 14430,"placement": "front"},
    "ACC-001": {"product_id": 74,  "variant_id": 4162, "placement": "embroidery_front"},
    "ACC-002": {"product_id": 143, "variant_id": 7542, "placement": "embroidery_front"},
}

# ── Cloudinary logo map (your existing logos) ─────────────────────────────────
COMPANY_LOGO_MAP = {
    "collegiate spirit co":  "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586397/collegiate-spirit-co-logo_zkp0ol.png",
    "corporate gifts inc":   "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586433/corporate-gifts-inc-logo_ohgcae.png",
    "corporate wellness llc":"https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586475/corporate-wellness-llc-logo_fdraoc.png",
    "eco adventures tours":  "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586587/eco-adventures-tours-logo_j6vskl.png",
    "summit events group":   "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/summit-events-group-logo.png",
}

# ── Request / Response models ─────────────────────────────────────────────────
class PrintfulMockupRequest(BaseModel):
    company_name: str
    sku: str

class PrintfulMockupResponse(BaseModel):
    status: str
    mockup_url: str
    company: str
    sku: str
    source: str  # "printful" | "cached"


# ── Helper: submit mockup task to Printful ─────────────────────────────────────
async def request_printful_mockup(product_id: int, variant_id: int,
                                   placement: str, logo_url: str) -> str:
    """
    Submits a mockup generation task to Printful and polls until complete.
    Returns the final mockup image URL.
    """
    headers = {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
        "Content-Type":  "application/json",
    }

    payload = {
        "variant_ids": [variant_id],
        "format": "jpg",
        "files": [
            {
                "placement": placement,
                "image_url": logo_url,
                "position": {
                    "area_width":  1800,
                    "area_height": 2400,
                    "width":       400,
                    "height":      400,
                    "top":         600,
                    "left":        700,
                },
            }
        ],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Submit task
        resp = await client.post(
            f"{PRINTFUL_BASE}/mockup-generator/create-task/{product_id}",
            headers=headers,
            json=payload,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Printful task creation failed: {resp.text}"
            )

        task_key = resp.json()["result"]["task_key"]

        # 2. Poll for result (Printful is async — usually 5–15 seconds)
        for attempt in range(20):
            await asyncio.sleep(3)
            poll = await client.get(
                f"{PRINTFUL_BASE}/mockup-generator/task?task_key={task_key}",
                headers=headers,
            )
            result = poll.json().get("result", {})
            status = result.get("status")

            if status == "completed":
                # Grab the first mockup image URL
                mockups = result.get("mockups", [])
                if mockups:
                    return mockups[0]["mockup_url"]
                raise HTTPException(status_code=500, detail="Printful returned no mockup images.")

            if status == "failed":
                raise HTTPException(status_code=500, detail="Printful mockup task failed.")

        raise HTTPException(status_code=504, detail="Printful mockup timed out after 60s.")


# ── Helper: cache mockup in Cloudinary ────────────────────────────────────────
def cache_mockup_cloudinary(mockup_url: str, slug: str, sku: str) -> str:
    """Downloads Printful mockup and re-uploads to your Cloudinary account."""
    result = cloudinary.uploader.upload(
        mockup_url,
        public_id=f"mockups/printful/{slug}/{sku}",
        overwrite=True,
        resource_type="image",
    )
    return result["secure_url"]


def get_cached_mockup(slug: str, sku: str) -> Optional[str]:
    """Check if a mockup is already cached in Cloudinary."""
    try:
        from cloudinary.api import resource
        res = resource(f"mockups/printful/{slug}/{sku}")
        return res.get("secure_url")
    except Exception:
        return None


# ── Main endpoint ──────────────────────────────────────────────────────────────
@router.post("/generate", response_model=PrintfulMockupResponse)
async def generate_printful_mockup(req: PrintfulMockupRequest):
    """
    Generates a photorealistic product mockup using Printful's Mockup Generator API.
    Composites the company logo onto the correct Urban Threads product.
    Caches result in Cloudinary under mockups/printful/{slug}/{sku}.
    """
    slug = req.company_name.strip().lower().replace(" ", "-")
    sku  = req.sku.upper().strip()

    # 1. Return cached mockup if already generated
    cached = get_cached_mockup(slug, sku)
    if cached:
        return PrintfulMockupResponse(
            status="cached",
            mockup_url=cached,
            company=req.company_name,
            sku=sku,
            source="cached",
        )

    # 2. Look up logo URL
    logo_url = COMPANY_LOGO_MAP.get(req.company_name.strip().lower())
    if not logo_url:
        raise HTTPException(
            status_code=404,
            detail=f"No logo found for company: {req.company_name}. "
                   f"Available: {list(COMPANY_LOGO_MAP.keys())}"
        )

    # 3. Look up Printful template
    template = SKU_TEMPLATE_MAP.get(sku)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"No Printful template mapped for SKU: {sku}. "
                   f"Available: {list(SKU_TEMPLATE_MAP.keys())}"
        )

    # 4. Generate mockup via Printful
    printful_url = await request_printful_mockup(
        product_id=template["product_id"],
        variant_id=template["variant_id"],
        placement=template["placement"],
        logo_url=logo_url,
    )

    # 5. Cache in Cloudinary
    final_url = cache_mockup_cloudinary(printful_url, slug, sku)

    return PrintfulMockupResponse(
        status="success",
        mockup_url=final_url,
        company=req.company_name,
        sku=sku,
        source="printful",
    )

@router.get("/stores")
async def list_printful_stores():
    """Returns your Printful stores — use to find your store_id."""
    headers = {"Authorization": f"Bearer {PRINTFUL_API_KEY}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{PRINTFUL_BASE}/stores", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ── Utility: list available products from Printful ────────────────────────────
@router.get("/products")
async def list_printful_products():
    """Returns Printful's full product catalog — use to verify template IDs."""
    headers = {"Authorization": f"Bearer {PRINTFUL_API_KEY}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{PRINTFUL_BASE}/products", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()