# mockup_routes.py
import httpx
import base64
import io
import os

import cloudinary
import cloudinary.uploader
import cloudinary.api
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ai-campaigns", tags=["Mockups"])

# ── Initialize Cloudinary ──────────────────────────────────────────────────────
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dp0cdq8bj"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

# ── Company → Logo URL map ─────────────────────────────────────────────────────
COMPANY_LOGO_MAP = {
    "collegiate spirit co":          "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586397/collegiate-spirit-co-logo_zkp0ol.png",
    "corporate gifts inc":           "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586433/corporate-gifts-inc-logo_ohgcae.png",
    "corporate wellness llc":        "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586475/corporate-wellness-llc-logo_fdraoc.png",
    "eco adventures tours":          "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586587/eco-adventures-tours-logo_j6vskl.png",
    "fitlife gyms":                  "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586540/fitlife-gyms-logo_bml45k.png",
    "ngo relief partners":           "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586622/ngo_relief_partners-logo_bwbjsw.png",
    "premium resorts intl":          "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586368/premium-resorts-intl-logo_yf57ak.png",
    "premium resorts international": "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586368/premium-resorts-intl-logo_yf57ak.png",
    "premium resorts int'l":         "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586368/premium-resorts-intl-logo_yf57ak.png",
    "summit events group":           "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586654/summit-events-group-logo_kv0rxk.png",
    "techwear co":                   "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586721/TechWear-co-logo_dzxowy.png",
    "urban streetwear collective":   "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775586696/urban-streetwear-collective-logo_wvpvsh.png",
}

def get_logo_url(company_name: str) -> Optional[str]:
    """Lookup logo — normalizes apostrophes and casing."""
    key = company_name.strip().lower()
    return COMPANY_LOGO_MAP.get(key)

class MockupRequest(BaseModel):
    company_name:      str
    sku:               str
    product_image_url: str
    placement:         str = "left chest"
    technique:         str = "embroidered"


def get_cached_mockup(slug: str, sku: str):
    try:
        result = cloudinary.api.resource(f"mockups/{slug}/{sku}")
        return result["secure_url"]
    except Exception:
        return None


def convert_to_rgba_png(image_bytes: bytes, size: tuple = (1024, 1024)) -> bytes:
    """Convert any image to RGBA PNG at the required square size for DALL-E 2."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    img = img.resize(size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_to_cloudinary(image_bytes: bytes, public_id: str) -> dict:
    return cloudinary.uploader.upload(
        io.BytesIO(image_bytes),
        public_id=public_id,
        overwrite=True,
        resource_type="image",
    )


@router.post("/generate-mockup")
async def generate_product_mockup(req: MockupRequest):
    """
    Generates a branded product mockup using DALL-E 2 image editing.
    Composites the company logo onto the product as embroidered/printed.
    Caches result in Cloudinary under mockups/{slug}/{sku}.
    """
    slug = req.company_name.strip().lower().replace(" ", "-")

    # 1. Return cached mockup if already generated
    cached = get_cached_mockup(slug, req.sku)
    if cached:
        return {
            "status": "cached",
            "mockup_url": cached,
            "company": req.company_name,
            "sku": req.sku,
        }

    # 2. Look up logo URL
    logo_url = get_logo_url(req.company_name)
    if not logo_url:
        raise HTTPException(
            status_code=404,
            detail=f"No logo found for: {req.company_name}"
        )

    # 3. Fetch both images
    async with httpx.AsyncClient(timeout=30.0) as client:
        product_resp = await client.get(req.product_image_url)
        logo_resp    = await client.get(logo_url)

    # 4. Convert both to RGBA PNG (required by DALL-E 2)
    product_png = convert_to_rgba_png(product_resp.content)
    logo_png    = convert_to_rgba_png(logo_resp.content)

    # 5. Build prompt
    placement_desc = {
        "left chest":   "the upper-left chest area",
        "center chest": "the center chest",
        "back":         "the upper back yoke area",
    }.get(req.placement, "the upper-left chest area")

    technique_desc = {
        "embroidered":    "embroidered with visible raised thread texture and stitching detail",
        "screen printed": "screen printed with slight ink spread and fabric texture showing through",
        "heat transfer":  "heat transfer applied with a smooth, slightly glossy finish on the fabric",
    }.get(req.technique, "embroidered with visible raised thread texture and stitching detail")

    prompt = (
        f"A professional product mockup of a garment with a brand logo {technique_desc} "
        f"on {placement_desc}. The logo conforms naturally to the fabric surface. "
        f"White background. Clean e-commerce photography style. "
        f"The garment is otherwise completely unchanged."
    )

    # 6. POST to DALL-E 2 images/edits
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    async with httpx.AsyncClient(timeout=120.0) as ai_client:
        api_response = await ai_client.post(
            "https://api.openai.com/v1/images/edits",
            headers={"Authorization": f"Bearer {openai_api_key}"},
            files={
                "image": ("product.png", io.BytesIO(product_png), "image/png"),
                "mask":  ("mask.png",    io.BytesIO(logo_png),    "image/png"),
            },
            data={
                "model":           "dall-e-2",
                "prompt":          prompt,
                "n":               "1",
                "size":            "1024x1024",
                "response_format": "b64_json",
            },
        )

    if api_response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI API error {api_response.status_code}: {api_response.text}"
        )

    # 7. Decode result
    result_b64   = api_response.json()["data"][0]["b64_json"]
    result_bytes = base64.b64decode(result_b64)

    # 8. Upload to Cloudinary
    cloudinary_result = upload_to_cloudinary(
        result_bytes,
        public_id=f"mockups/{slug}/{req.sku}",
    )

    return {
        "status":     "success",
        "mockup_url": cloudinary_result["secure_url"],
        "company":    req.company_name,
        "sku":        req.sku,
        "placement":  req.placement,
        "technique":  req.technique,
    }