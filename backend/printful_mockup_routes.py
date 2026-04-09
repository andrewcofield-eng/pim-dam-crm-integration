# backend/printful_mockup_routes.py

import os
import asyncio
import httpx
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/printful-mockups", tags=["Printful Mockups"])

PRINTFUL_API_KEY  = os.getenv("PRINTFUL_API_KEY")
PRINTFUL_STORE_ID = os.getenv("PRINTFUL_STORE_ID")
PRINTFUL_BASE     = "https://api.printful.com"

# ── SKU → Printful Product + Variant IDs ──────────────────────────────────────
SKU_TEMPLATE_MAP = {

    # Unisex Heavy Cotton Tee — large center chest, printfile 1: 1800×2400
    "TOP-001": {
        "product_id": 71, "variant_id": 4011, "placement": "front",
        "position": {"area_width": 1800, "area_height": 2400, "width": 900, "height": 450, "top": 400, "left": 450, "limit_to_print_area": True},
    },

    # DTFabric Tee — large center chest, printfile 1340: 4200×5400
    "TOP-002": {
        "product_id": 1414, "variant_id": 33937, "placement": "front_dtfabric",
        "position": {"area_width": 4200, "area_height": 5400, "width": 2000, "height": 1000, "top": 900, "left": 1100, "limit_to_print_area": True},
    },

    # Performance Polo — small left chest, printfile 1: 1800×2400
    "TOP-003": {
        "product_id": 108, "variant_id": 4865, "placement": "front",
        "position": {"area_width": 1800, "area_height": 2400, "width": 380, "height": 190, "top": 320, "left": 220, "limit_to_print_area": True},
    },

    # Pullover Hoodie — large center chest, printfile 139: 2100×2100
    "HOD-001": {
        "product_id": 146, "variant_id": 5522, "placement": "front",
        "position": {"area_width": 2100, "area_height": 2100, "width": 900, "height": 450, "top": 350, "left": 600, "limit_to_print_area": True},
    },

    # Zip Hoodie — small LEFT chest (zipper blocks center), printfile 306: 1950×1950
    "HOD-002": {
        "product_id": 584, "variant_id": 15038, "placement": "front",
        "position": {"area_width": 1950, "area_height": 1950, "width": 420, "height": 210, "top": 300, "left": 180, "limit_to_print_area": True},
    },

    # DTF Hat — wide center front panel, printfile 816: 1500×600
    "ACC-001": {
        "product_id": 952, "variant_id": 24379, "placement": "front_dtf_hat",
        "position": {"area_width": 1500, "area_height": 600, "width": 700, "height": 280, "top": 160, "left": 400, "limit_to_print_area": True},
    },

    # Beanie — front embroidery, printfile 74: 1500×525
    "ACC-002": {
        "product_id": 81, "variant_id": 4522, "placement": "embroidery_front",
        "position": {"area_width": 1500, "area_height": 525, "width": 600, "height": 240, "top": 143, "left": 450, "limit_to_print_area": True},
    },
}
# ── Cloudinary logo map ────────────────────────────────────────────────────────
COMPANY_LOGO_MAP = {
    "collegiate spirit co":   "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1775586397/collegiate-spirit-co-logo_zkp0ol.png",
    "corporate gifts inc":    "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1775586433/corporate-gifts-inc-logo_ohgcae.png",
    "corporate wellness llc": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1775586475/corporate-wellness-llc-logo_fdraoc.png",
    "eco adventures tours":   "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1775586587/eco-adventures-tours-logo_j6vskl.png",
    "summit events group":    "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1775586654/summit-events-group-logo_kv0rxk.png",
}

# ── Request / Response models ──────────────────────────────────────────────────
class PrintfulMockupRequest(BaseModel):
    company_name: str
    sku: str

class PrintfulMockupResponse(BaseModel):
    status: str
    mockup_url: str
    company: str
    sku: str
    source: str


# ── Helper: submit mockup task to Printful ─────────────────────────────────────
async def request_printful_mockup(
    product_id: int,
    variant_id: int,
    placement: str,
    logo_url: str,
    position: dict,          # ← add this
) -> str:
    headers = {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
        "Content-Type":  "application/json",
        "X-PF-Store-Id": str(PRINTFUL_STORE_ID),
    }

    payload = {
        "variant_ids": [variant_id],
        "format":       "jpg",
        "files": [
            {
                "placement": placement,
                "image_url": logo_url,
                "position":  position,   # ← use passed-in position
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

        # 2. Poll for result (usually 5–15 seconds)
        for attempt in range(20):
            await asyncio.sleep(3)
            poll = await client.get(
                f"{PRINTFUL_BASE}/mockup-generator/task?task_key={task_key}",
                headers=headers,
            )
            result = poll.json().get("result", {})
            status = result.get("status")

            if status == "completed":
                mockups = result.get("mockups", [])
                if mockups:
                    return mockups[0]["mockup_url"]
                raise HTTPException(status_code=500, detail="Printful returned no mockup images.")

            print(f"[PRINTFUL POLL] attempt={attempt} raw={poll.text}", flush=True)

            if status == "failed":
                error_detail = result.get("error", poll.text)
                raise HTTPException(
                    status_code=500,
                    detail=f"Printful mockup task failed: {error_detail}"
                )

        raise HTTPException(status_code=504, detail="Printful mockup timed out after 60s.")

# ── Helper: cache mockup in Cloudinary ────────────────────────────────────────
def cache_mockup_cloudinary(mockup_url: str, slug: str, sku: str) -> str:
    result = cloudinary.uploader.upload(
        mockup_url,
        public_id=f"mockups/printful/{slug}/{sku}",
        overwrite=True,
        resource_type="image",
    )
    return result["secure_url"]


def get_cached_mockup(slug: str, sku: str) -> Optional[str]:
    try:
        from cloudinary.api import resource
        res = resource(f"mockups/printful/{slug}/{sku}")
        return res.get("secure_url")
    except Exception:
        return None


# ── Helper: compute aspect-ratio-correct position ─────────────────────────────
async def get_image_dimensions(url: str) -> tuple[int, int]:
    """Fetch logo and return its natural pixel dimensions."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(resp.content))
    return img.width, img.height


def compute_position(
    logo_w: int,
    logo_h: int,
    area_w: int,
    area_h: int,
    target_w: int,
    top: int,
    left_center: int,
) -> dict:
    """Scales logo to target_w, preserving aspect ratio, centered on left_center."""
    ratio = logo_h / logo_w
    w = target_w
    h = int(target_w * ratio)
    left = left_center - (w // 2)
    return {
        "area_width":  area_w,
        "area_height": area_h,
        "width":       w,
        "height":      h,
        "top":         top,
        "left":        max(0, left),
        "limit_to_print_area": True,
    }


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

    # 4. Fetch logo dimensions and compute aspect-correct position
    logo_w, logo_h = await get_image_dimensions(logo_url)
    pos_cfg = template["position"]
    position = compute_position(
        logo_w=logo_w,
        logo_h=logo_h,
        area_w=pos_cfg["area_width"],
        area_h=pos_cfg["area_height"],
        target_w=pos_cfg["width"],
        top=pos_cfg["top"],
        left_center=pos_cfg["left"] + pos_cfg["width"] // 2,
    )

    # 5. Generate mockup via Printful
    printful_url = await request_printful_mockup(
        product_id=template["product_id"],
        variant_id=template["variant_id"],
        placement=template["placement"],
        logo_url=logo_url,
        position=position,
    )

    # 6. Cache in Cloudinary
    final_url = cache_mockup_cloudinary(printful_url, slug, sku)

    return PrintfulMockupResponse(
        status="success",
        mockup_url=final_url,
        company=req.company_name,
        sku=sku,
        source="printful",
    )

# ── Utility endpoints ──────────────────────────────────────────────────────────
@router.get("/stores")
async def list_printful_stores():
    """Returns your Printful stores — use to find your store_id."""
    headers = {"Authorization": f"Bearer {PRINTFUL_API_KEY}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{PRINTFUL_BASE}/stores", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/products")
async def list_printful_products():
    """Returns Printful's full product catalog — use to verify template IDs."""
    headers = {"Authorization": f"Bearer {PRINTFUL_API_KEY}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{PRINTFUL_BASE}/products", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@router.get("/products/{product_id}/variants")
async def get_product_variants(product_id: int):
    """Returns all variants for a Printful product — use to find correct variant_ids."""
    headers = {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
        "X-PF-Store-Id": str(PRINTFUL_STORE_ID),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PRINTFUL_BASE}/mockup-generator/printfiles/{product_id}",
            headers=headers,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

