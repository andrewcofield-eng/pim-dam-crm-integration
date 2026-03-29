"""
campaign_html_routes.py
=======================
New AgenticFlow campaign generator endpoints.
Generates personalized, downloadable HTML email + landing page.

Add to main.py:
    from campaign_html_routes import router as html_campaign_router
    app.include_router(html_campaign_router)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import json
from datetime import datetime, timezone
from openai import OpenAI

router = APIRouter(prefix="/html-campaign", tags=["HTML Campaign Generator"])

BASE_URL      = "https://pim-dam-crm-integration-production-62d7.up.railway.app"
DIRECTUS_URL  = os.getenv("DIRECTUS_URL", "https://directus-production-9f53.up.railway.app")
DIRECTUS_TOKEN= os.getenv("DIRECTUS_TOKEN", "")
CL_CLOUD      = "dp0cdq8bj"

# ------ Brand config ---------------------------------------------------------------------------------------------------------------------------------------
BRAND = {
    "name":     "Urban Threads",
    "charcoal": "#1C1C1C",
    "gold":     "#D4AF37",
    "cream":    "#F5F0E8",
    "tan":      "#C4A882",
    "slate":    "#6B7280",
    "tagline":  "Own the Street.",
    "season":   "Spring / Summer 2026",
}

# ------ Cloudinary lifestyle hero pool ---------------------------------------------------------------------------------
HERO_IMAGES = {
    "default":         "v1774727348/HOD-001_ACC_001City_street_heelsWoman_w18vkt.png",
    "rooftop_couple":  "v1774727354/HOD-001_ACC_001Rooftopcouple_oh5qrh.png",
    "wall_woman":      "v1774727359/HOD-001_ACC_001wallWoman_a0mjrd.png",
    "car_couple":      "v1774727347/HOD-001_ACC_001carhoodcouple_jboayc.png",
    "rooftop_man":     "v1774727352/HOD-001_ACC_001Rooftop_man_thivq3.png",
    "coffee_man":      "v1774727363/KNIT-001coffeeshopMan_rvhsik.png",
    "rain_woman":      "v1774727365/OUT-001RainStreetwoman_zyssut.png",
    "steps_man":       "v1774727367/OUT-002_KNIT-001_DNM-003_ACC-002stepsman_pvdcbn.png",
    "street_man":      "v1774727349/HOD-001_ACC_001City_street_man_snxgbx.png",
    "lounge_couple":   "v1774727351/HOD-001_ACC_001Loungecouple_y2dkph.png",
    "steps_woman":     "v1774727356/HOD-001_ACC_001stepsWoman_nsahrx.png",
    "street_couple":   "v1774727358/HOD-001_ACC_001wallStreetcouple_cvrzcx.png",
}

# ------ Segment --- hero image + product category affinity ---------------------------
SEGMENT_CONFIG = {
    "Health & Wellness": {
        "hero":       "steps_man",
        "categories": ["Hoodies", "Outerwear", "Activewear"],
        "headline_hook": "Built to perform. Designed to last.",
    },
    "Sports": {
        "hero":       "street_man",
        "categories": ["Hoodies", "Activewear", "Accessories"],
        "headline_hook": "Game-ready gear for your whole team.",
    },
    "Agency": {
        "hero":       "coffee_man",
        "categories": ["Sweaters", "Shirts", "Accessories"],
        "headline_hook": "Creative culture starts with what you wear.",
    },
    "Tech / SaaS": {
        "hero":       "rooftop_couple",
        "categories": ["Hoodies", "Denim", "Accessories"],
        "headline_hook": "For teams that ship fast and dress sharp.",
    },
    "Hospitality": {
        "hero":       "lounge_couple",
        "categories": ["Shirts", "Outerwear", "Accessories"],
        "headline_hook": "First impressions, premium apparel.",
    },
    "default": {
        "hero":       "default",
        "categories": ["Hoodies", "Outerwear", "Denim"],
        "headline_hook": "Premium streetwear built for every moment.",
    },
}


# ------ Request model ---------------------------------------------------------------------------------------------------------------------------------------
class CampaignRequest(BaseModel):
    company:       str
    contact_name:  str
    contact_title: str
    contact_email: str
    segment:       str
    abm_score:     int
    deal_value:    str
    stage:         str
    tone:          Optional[str] = "Confident"
    hero_image_key: Optional[str] = None
    selected_skus:  Optional[List[str]] = None
    variant:        Optional[str] = "A"       # A/B testing
    directus_token: Optional[str] = ""
    directus_url:   Optional[str] = ""


# ------ Helpers ---------------------------------------------------------------------------------------------------------------------------------------------------------
def cl_url(path: str, transform: str = "f_auto,q_auto") -> str:
    return f"https://res.cloudinary.com/{CL_CLOUD}/image/upload/{transform}/{path}"


async def fetch_products(skus=None, token=None, url=None):
    """Fetch products from our own FastAPI /products endpoint - always works."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("http://localhost:8000/products")
            print(f"[fetch_products] self-call status={r.status_code}", flush=True)
            raw = r.json()
            if isinstance(raw, list):
                all_prods = raw
            elif "value" in raw:
                all_prods = raw["value"]
            else:
                all_prods = raw.get("data", [])
            # Normalize field names: product_name -> name
            for p in all_prods:
                if "product_name" in p and "name" not in p:
                    p["name"] = p["product_name"]
                if "short_description" in p and "description" not in p:
                    p["description"] = p["short_description"]
            print(f"[fetch_products] total={len(all_prods)} skus_filter={skus}", flush=True)
            if skus:
                filtered = [p for p in all_prods if p.get("sku") in skus]
                print(f"[fetch_products] filtered={len(filtered)}", flush=True)
                return filtered[:6] if filtered else all_prods[:4]
            return all_prods[:6]
    except Exception as e:
        print(f"[fetch_products] error: {e}", flush=True)
        return []


def build_product_cards_email(products: List[dict]) -> str:
    """Render 2-column product grid for email (inline CSS)."""
    if not products:
        return ""
    rows = []
    for i in range(0, min(len(products), 4), 2):
        left  = products[i]
        right = products[i+1] if i+1 < len(products) else None
        img_l = cl_url(left.get("cloudinary_url","").replace(f"https://res.cloudinary.com/{CL_CLOUD}/image/upload/","") or "v1773412902/image-img_HOD-001.png", "c_fill,w_268,h_268,f_auto,q_auto")
        card_l = f"""
        <td width="48%" style="vertical-align:top;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #E5E0D8;">
            <tr><td><img src="{img_l}" width="268" style="display:block;width:100%;border:0;" /></td></tr>
            <tr><td style="padding:16px;">
              <p style="margin:0 0 2px;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#D4AF37;">{left.get("category","")} --- {left.get("sku","")}</p>
              <h3 style="margin:0 0 6px;font-size:15px;font-weight:700;color:#1C1C1C;">{left.get("name","")}</h3>
              <p style="margin:0 0 12px;font-size:17px;font-weight:700;color:#1C1C1C;">${left.get("price","")}</p>
              <a href="#" style="display:block;text-align:center;background:#1C1C1C;color:#D4AF37;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:10px;text-decoration:none;">SHOP NOW</a>
            </td></tr>
          </table>
        </td>"""
        if right:
            img_r = cl_url(right.get("cloudinary_url","").replace(f"https://res.cloudinary.com/{CL_CLOUD}/image/upload/","") or "v1773412900/image-img_OUT-001.png", "c_fill,w_268,h_268,f_auto,q_auto")
            card_r = f"""
        <td width="4%">&nbsp;</td>
        <td width="48%" style="vertical-align:top;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #E5E0D8;">
            <tr><td><img src="{img_r}" width="268" style="display:block;width:100%;border:0;" /></td></tr>
            <tr><td style="padding:16px;">
              <p style="margin:0 0 2px;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#D4AF37;">{right.get("category","")} --- {right.get("sku","")}</p>
              <h3 style="margin:0 0 6px;font-size:15px;font-weight:700;color:#1C1C1C;">{right.get("name","")}</h3>
              <p style="margin:0 0 12px;font-size:17px;font-weight:700;color:#1C1C1C;">${right.get("price","")}</p>
              <a href="#" style="display:block;text-align:center;background:#1C1C1C;color:#D4AF37;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:10px;text-decoration:none;">SHOP NOW</a>
            </td></tr>
          </table>
        </td>"""
        else:
            card_r = '<td width="52%">&nbsp;</td>'
        rows.append(f'<tr>{card_l}{card_r}</tr>')
    return "\n".join(rows)


def build_product_cards_lp(products: List[dict]) -> str:
    """Render product cards for landing page."""
    cards = []
    for p in products[:6]:
        img_url = p.get("cloudinary_url") or ""
        raw_path = img_url.replace(f"https://res.cloudinary.com/{CL_CLOUD}/image/upload/","")
        img = cl_url(raw_path or "v1773412902/image-img_HOD-001.png", "c_fill,w_600,h_600,f_auto,q_auto")
        name  = p.get("name") or p.get("product_name") or "Product"
        sku   = p.get("sku") or ""
        price = p.get("price") or ""
        desc  = p.get("description") or p.get("short_description") or p.get("Description") or ""
        cat   = p.get("category") or ""
        try:
            price_fmt = f"${float(price):.2f}" if price else ""
        except Exception:
            price_fmt = str(price)
        cards.append(
            f'''<div style="background:#fff;border:1px solid #E5E0D8;">'''
            f'''<img src="{img}" style="display:block;width:100%;aspect-ratio:1/1;object-fit:cover;" />'''
            f'''<div style="padding:20px;">'''
            f'''<p style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#6B7280;margin-bottom:6px;">{cat}</p>'''
            f'''<p style="font-family:'Bebas Neue',sans-serif;font-size:20px;letter-spacing:2px;color:#1C1C1C;margin-bottom:8px;">{name}</p>'''
            f'''<p style="font-size:13px;color:#6B7280;margin-bottom:12px;line-height:1.5;">{desc[:100]}...</p>'''
            f'''<div style="display:flex;justify-content:space-between;align-items:center;">'''
            f'''<span style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:#D4AF37;">{price_fmt}</span>'''
            f'''<a href="#" style="background:#1C1C1C;color:#D4AF37;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:8px 16px;">Order</a>'''
            f'''</div></div></div>'''
        )
    return "\n".join(cards)


def pick_hero(segment: str = None, override_key: str = None) -> str:
    try:
        key = override_key if override_key and override_key in HERO_IMAGES else None
        if not key and segment:
            cfg = SEGMENT_CONFIG.get(segment, SEGMENT_CONFIG.get("default", {}))
            hero_key = cfg.get("hero", "default") if isinstance(cfg, dict) else "default"
            key = hero_key if hero_key in HERO_IMAGES else "default"
        if not key:
            key = "default"
        path = HERO_IMAGES.get(key, HERO_IMAGES.get("default", "v1774727359/HOD-001_ACC_001wallWoman_a0mjrd.png"))
        return cl_url(path, "c_fill,w_1400,h_900,f_auto,q_auto")
    except Exception as e:
        print(f"[pick_hero] error: {e}", flush=True)
        return cl_url("v1774727359/HOD-001_ACC_001wallWoman_a0mjrd.png", "c_fill,w_1400,h_900,f_auto,q_auto")


async def generate_copy_with_ai(req: CampaignRequest, products: list) -> dict:
    company = req.company or "Your Company"
    first = (req.contact_name or "there").split()[0]
    segment = req.segment or "Retail"
    return {
        "subject": "Urban Threads x " + company,
        "preview_text": "Hi " + first + ", your collection is ready.",
        "hero_headline": "BUILT FOR " + company[:20].upper(),
        "hero_subheadline": "Premium streetwear for " + segment + " teams.",
        "body_copy": "Hi " + first + ", we curated our best pieces for " + company + ".",
        "cta_primary": "Shop the Collection",
        "lp_headline": "YOUR EXCLUSIVE DROP",
        "lp_subheadline": "Curated for " + company + ". Built for the street.",
    }


def generate_email_html(req: CampaignRequest, copy: dict, products: List[dict], hero_url: str) -> str:
    product_grid = build_product_cards_email(products)
    lifestyle_url = cl_url("v1774727354/HOD-001_ACC_001Rooftopcouple_oh5qrh.png", "c_fill,w_600,h_300,f_auto,q_auto")
    variant_label = f"Variant {req.variant}" if req.variant != "A" else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Urban Threads --- {copy["subject_line"]}</title>
<!-- {variant_label} | Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} -->
<!-- Prospect: {req.company} | Segment: {req.segment} | Score: {req.abm_score} -->
</head>
<body style="margin:0;padding:0;background:#F5F0E8;font-family:Helvetica Neue,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0E8;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;">

<!-- Gold bar -->
<tr><td style="background:#D4AF37;height:4px;font-size:0;">&nbsp;</td></tr>

<!-- Hero image -->
<tr><td style="padding:0;background:#1C1C1C;">
  <img src="{hero_url}" alt="Urban Threads" width="600" style="display:block;width:100%;border:0;"/>
</td></tr>

<!-- Logo bar -->
<tr><td style="background:#1C1C1C;padding:18px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td><p style="margin:0;font-size:22px;font-weight:900;letter-spacing:4px;color:#fff;font-family:Impact,Arial Black,sans-serif;">URBAN<span style="color:#D4AF37;">THREADS</span></p></td>
    <td align="right"><p style="margin:0;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#C4A882;">{BRAND["season"]}</p></td>
  </tr></table>
</td></tr>
<tr><td style="background:#D4AF37;height:2px;font-size:0;">&nbsp;</td></tr>

<!-- Hero copy -->
<tr><td style="background:#1C1C1C;padding:40px 32px;text-align:center;">
  <p style="margin:0 0 10px;font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#D4AF37;">Exclusively for {req.company}</p>
  <h1 style="margin:0 0 14px;font-size:46px;line-height:1.0;font-weight:900;letter-spacing:3px;text-transform:uppercase;color:#fff;font-family:Impact,Arial Black,sans-serif;">{copy["headline"]}</h1>
  <p style="margin:0 0 8px;font-size:16px;font-weight:500;color:#D4AF37;">{copy["subheadline"]}</p>
  <p style="margin:0 0 28px;font-size:14px;line-height:1.7;color:#C4A882;max-width:440px;margin-left:auto;margin-right:auto;">{copy["body_copy"]}</p>
  <a href="#" style="display:inline-block;background:#D4AF37;color:#1C1C1C;font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:14px 36px;text-decoration:none;">{copy["cta_text"]}</a>
</td></tr>
<tr><td style="background:#D4AF37;height:2px;font-size:0;">&nbsp;</td></tr>

<!-- Product grid header -->
<tr><td style="background:#F5F0E8;padding:32px 32px 16px;text-align:center;">
  <p style="margin:0 0 6px;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#D4AF37;">Curated for {req.segment}</p>
  <h2 style="margin:0;font-size:26px;font-weight:900;letter-spacing:2px;text-transform:uppercase;color:#1C1C1C;font-family:Impact,Arial Black,sans-serif;">YOUR TEAM'S COLLECTION</h2>
</td></tr>

<!-- Product grid -->
<tr><td style="background:#F5F0E8;padding:0 24px 24px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    {product_grid}
  </table>
</td></tr>

<!-- Lifestyle image -->
<tr><td style="background:#D4AF37;height:2px;font-size:0;">&nbsp;</td></tr>
<tr><td style="padding:0;">
  <img src="{lifestyle_url}" width="600" style="display:block;width:100%;border:0;" alt="Urban Threads Lifestyle"/>
</td></tr>
<tr><td style="background:#1C1C1C;padding:28px 32px;text-align:center;">
  <h2 style="margin:0 0 10px;font-size:28px;font-weight:900;letter-spacing:2px;text-transform:uppercase;color:#fff;font-family:Impact,Arial Black,sans-serif;">BUILT FOR BOTH.</h2>
  <p style="margin:0 0 20px;font-size:13px;color:#C4A882;">Custom logos -- Fast turnaround -- No minimums on select styles</p>
  <a href="#" style="display:inline-block;background:#D4AF37;color:#1C1C1C;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:12px 32px;text-decoration:none;">EXPLORE ALL STYLES</a>
</td></tr>

<!-- Promo strip -->
<tr><td style="background:#C4A882;padding:14px 32px;text-align:center;">
  <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#1C1C1C;">Free shipping over $75 &nbsp;|&nbsp; Custom quotes available &nbsp;|&nbsp; 30-day guarantee</p>
</td></tr>
<tr><td style="background:#D4AF37;height:2px;font-size:0;">&nbsp;</td></tr>

<!-- Footer -->
<tr><td style="background:#1C1C1C;padding:28px 32px;text-align:center;">
  <p style="margin:0 0 14px;font-size:19px;font-weight:900;letter-spacing:4px;color:#fff;font-family:Impact,Arial Black,sans-serif;">URBAN<span style="color:#D4AF37;">THREADS</span></p>
  <p style="margin:0 0 10px;">
    <a href="#" style="color:#D4AF37;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin:0 8px;">Shop</a>
    <a href="#" style="color:#C4A882;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin:0 8px;">About</a>
    <a href="#" style="color:#C4A882;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin:0 8px;">Contact</a>
    <a href="#" style="color:#C4A882;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin:0 8px;">Unsubscribe</a>
  </p>
  <p style="margin:0;font-size:10px;color:#6B7280;">&copy; 2026 Urban Threads -- 123 Urban Ave, New York, NY 10001<br/>
    <a href="#" style="color:#6B7280;text-decoration:underline;">Privacy Policy</a> &nbsp;|&nbsp; <a href="#" style="color:#6B7280;text-decoration:underline;">Terms</a>
  </p>
</td></tr>
<tr><td style="background:#D4AF37;height:4px;font-size:0;">&nbsp;</td></tr>

</table>
</td></tr></table>
</body></html>"""


def generate_landing_page_html(req: CampaignRequest, copy: dict, products: List[dict]) -> str:
    lp_hero_url = cl_url("v1774727359/HOD-001_ACC_001wallWoman_a0mjrd.png", "c_fill,w_1400,h_900,f_auto,q_auto")
    feature_url = cl_url("v1774727354/HOD-001_ACC_001Rooftopcouple_oh5qrh.png", "c_fill,w_800,h_700,f_auto,q_auto")
    product_cards = build_product_cards_lp(products)
    first_name = req.contact_name.split()[0]
    variant_label = f"Variant {req.variant}" if req.variant != "A" else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Urban Threads --- {copy["lp_headline"]} | {req.company}</title>
<!-- {variant_label} | Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} -->
<!-- Prospect: {req.company} | Segment: {req.segment} | Score: {req.abm_score} -->
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>
:root{{--c:#1C1C1C;--g:#D4AF37;--cr:#F5F0E8;--t:#C4A882;--s:#6B7280;--w:#FFFFFF;--r:#E5E0D8;
--fh:'Bebas Neue',Impact,sans-serif;--fb:'Inter',Helvetica Neue,Arial,sans-serif;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--cr);color:var(--c);font-family:var(--fb);}}
a{{text-decoration:none;}}img{{display:block;max-width:100%;}}
.gold-rule{{height:3px;background:var(--g);}}
.container{{max-width:1200px;margin:0 auto;padding:0 24px;}}
nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:var(--c);border-bottom:2px solid var(--g);}}
.nav-inner{{max-width:1200px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:60px;}}
.nav-brand{{font-family:var(--fh);font-size:24px;letter-spacing:3px;color:var(--w);}}
.nav-brand span{{color:var(--g);}}
.nav-links{{display:flex;gap:28px;align-items:center;}}
.nav-links a{{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--t);transition:color 0.2s;}}
.nav-links a:hover{{color:var(--g);}}
.nav-cta{{background:var(--g);color:var(--c)!important;padding:8px 20px;font-weight:700!important;}}
.hero{{position:relative;min-height:100vh;display:flex;align-items:flex-end;overflow:hidden;padding-top:60px;}}
.hero-bg{{position:absolute;inset:0;background-image:url('{lp_hero_url}');background-size:cover;background-position:center top;opacity:0.55;}}
.hero-overlay{{position:absolute;inset:0;background:linear-gradient(to top,rgba(28,28,28,0.97) 0%,rgba(28,28,28,0.2) 60%,transparent 100%);}}
.hero-content{{position:relative;z-index:2;padding:0 24px 80px;max-width:1200px;margin:0 auto;width:100%;}}
.hero-label{{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:var(--g);margin-bottom:14px;}}
.hero-hl{{font-family:var(--fh);font-size:clamp(56px,9vw,108px);line-height:0.95;letter-spacing:4px;color:var(--w);text-transform:uppercase;margin-bottom:20px;}}
.hero-hl em{{color:var(--g);font-style:normal;}}
.hero-sub{{font-size:17px;line-height:1.6;color:var(--t);max-width:480px;margin-bottom:32px;}}
.hero-actions{{display:flex;gap:16px;flex-wrap:wrap;}}
.btn-p{{display:inline-block;background:var(--g);color:var(--c);font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:16px 40px;transition:background 0.2s;}}
.btn-p:hover{{background:var(--t);}}
.btn-s{{display:inline-block;border:2px solid var(--g);color:var(--g);font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:14px 36px;transition:all 0.2s;}}
.btn-s:hover{{background:var(--g);color:var(--c);}}
.marquee{{background:var(--g);padding:9px 0;overflow:hidden;white-space:nowrap;}}
.marquee-track{{display:inline-block;animation:mq 18s linear infinite;font-family:var(--fh);font-size:14px;letter-spacing:3px;color:var(--c);}}
@keyframes mq{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.section{{padding:72px 0;}}
.section-label{{font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--g);margin-bottom:6px;}}
.section-title{{font-family:var(--fh);font-size:clamp(32px,5vw,56px);letter-spacing:3px;text-transform:uppercase;color:var(--c);}}
.section-sub{{font-size:14px;color:var(--s);margin-top:10px;}}
.product-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:24px;margin-top:40px;}}
.product-grid>div{{transition:transform 0.2s,box-shadow 0.2s;}}
.product-grid>div:hover{{transform:translateY(-4px);box-shadow:0 12px 32px rgba(28,28,28,0.1);}}
.stats-strip{{background:var(--c);padding:48px 0;}}
.stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:32px;text-align:center;}}
.stat-num{{font-family:var(--fh);font-size:52px;color:var(--g);}}
.stat-lbl{{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--t);margin-top:4px;}}
.feature{{display:grid;grid-template-columns:1fr 1fr;min-height:520px;}}
.feature-img{{overflow:hidden;}}
.feature-img img{{width:100%;height:100%;object-fit:cover;}}
.feature-body{{background:var(--c);display:flex;flex-direction:column;justify-content:center;padding:56px;}}
.feature-title{{font-family:var(--fh);font-size:clamp(32px,4vw,52px);letter-spacing:3px;text-transform:uppercase;color:var(--w);line-height:1;margin:12px 0 18px;}}
.feature-copy{{font-size:14px;line-height:1.7;color:var(--t);margin-bottom:28px;}}
.signup{{background:var(--cr);padding:72px 0;text-align:center;border-top:1px solid var(--r);}}
.signup-form{{display:flex;max-width:460px;margin:24px auto 0;}}
.signup-input{{flex:1;padding:14px 18px;border:2px solid var(--c);border-right:none;font-size:13px;outline:none;}}
.signup-btn{{background:var(--c);color:var(--g);border:2px solid var(--c);padding:14px 24px;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;cursor:pointer;transition:all 0.2s;}}
.signup-btn:hover{{background:var(--g);color:var(--c);border-color:var(--g);}}
footer{{background:var(--c);padding:48px 0 28px;border-top:3px solid var(--g);}}
.footer-grid{{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:40px;margin-bottom:40px;}}
.footer-brand{{font-family:var(--fh);font-size:28px;letter-spacing:3px;color:var(--w);margin-bottom:10px;}}
.footer-brand span{{color:var(--g);}}
.footer-tag{{font-size:12px;line-height:1.6;color:var(--t);max-width:240px;}}
.fc-title{{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--g);margin-bottom:14px;}}
.fc-links{{list-style:none;}}
.fc-links li{{margin-bottom:9px;}}
.fc-links a{{font-size:13px;color:var(--t);transition:color 0.2s;}}
.fc-links a:hover{{color:var(--g);}}
.footer-bottom{{border-top:1px solid #2A2A2A;padding-top:20px;display:flex;justify-content:space-between;}}
.footer-legal{{font-size:11px;color:var(--s);}}
.footer-legal a{{color:var(--s);text-decoration:underline;}}
@media(max-width:768px){{
  .nav-links{{display:none;}}
  .feature{{grid-template-columns:1fr;}}
  .feature-body{{padding:36px 24px;}}
  .stats-grid{{grid-template-columns:repeat(2,1fr);}}
  .footer-grid{{grid-template-columns:1fr 1fr;}}
  .footer-bottom{{flex-direction:column;gap:10px;}}
  .signup-form{{flex-direction:column;}}
  .signup-input{{border-right:2px solid var(--c);border-bottom:none;}}
}}
</style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <div class="nav-brand">URBAN<span>THREADS</span></div>
    <div class="nav-links">
      <a href="#collection">Collection</a>
      <a href="#lifestyle">Lifestyle</a>
      <a href="#" class="nav-cta">Get a Quote</a>
    </div>
  </div>
</nav>

<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <p class="hero-label">For {req.company} -- {req.segment} -- SS2026</p>
    <h1 class="hero-hl">{copy["lp_headline"].replace(" ", "<br/>", 1)}</h1>
    <p class="hero-sub">{copy["lp_body"]}</p>
    <div class="hero-actions">
      <a href="#collection" class="btn-p">{copy["cta_text"]}</a>
      <a href="#lifestyle" class="btn-s">See the Lookbook</a>
    </div>
  </div>
</section>

<div class="gold-rule"></div>
<div class="marquee">
  <div class="marquee-track">PREMIUM QUALITY &nbsp;--&nbsp; FREE SHIPPING OVER $75 &nbsp;--&nbsp; CUSTOM LOGOS &nbsp;--&nbsp; BUILT TO LAST &nbsp;--&nbsp; OWN THE STREET &nbsp;--&nbsp; FREE RETURNS &nbsp;--&nbsp; PREMIUM QUALITY &nbsp;--&nbsp; FREE SHIPPING OVER $75 &nbsp;--&nbsp; CUSTOM LOGOS &nbsp;--&nbsp; BUILT TO LAST &nbsp;--&nbsp; OWN THE STREET &nbsp;--&nbsp; FREE RETURNS &nbsp;--&nbsp;</div>
</div>
<div class="gold-rule"></div>

<section class="section" id="collection" style="background:var(--cr);">
  <div class="container">
    <p class="section-label">Curated for {req.segment}</p>
    <h2 class="section-title">Your Team's Collection</h2>
    <p class="section-sub">Heavyweight fabrics. Precise stitching. Custom logos available.</p>
    <div class="product-grid">{product_cards}</div>
  </div>
</section>

<div class="stats-strip">
  <div class="container">
    <div class="stats-grid">
      <div><div class="stat-num">380</div><div class="stat-lbl">GSM Fleece Weight</div></div>
      <div><div class="stat-num">30+</div><div class="stat-lbl">Active SKUs</div></div>
      <div><div class="stat-num">48h</div><div class="stat-lbl">Campaign Turnaround</div></div>
      <div><div class="stat-num">100%</div><div class="stat-lbl">Satisfaction Guarantee</div></div>
    </div>
  </div>
</div>

<section class="feature" id="lifestyle">
  <div class="feature-img">
    <img src="{feature_url}" alt="Urban Threads Lifestyle" />
  </div>
  <div class="feature-body">
    <p class="section-label">The Lookbook</p>
    <h2 class="feature-title">BUILT FOR<br/><span style="color:#D4AF37">BOTH.</span></h2>
    <p class="feature-copy">From morning runs to rooftop bars. From the boardroom to the weekend. Urban Threads moves with your team --- not against it. Data-informed design. AI-powered speed. Human at the core.</p>
    <a href="#" class="btn-p" style="align-self:flex-start;">View the Lookbook</a>
  </div>
</section>

<section class="signup">
  <div class="container">
    <p class="section-label">Stay in the Loop</p>
    <h2 class="section-title" style="margin-top:6px;">Get Early Access</h2>
    <p class="section-sub">New drops. Exclusive offers. Zero noise.</p>
    <form class="signup-form" onsubmit="return false;">
      <input class="signup-input" type="email" placeholder="your@email.com"/>
      <button class="signup-btn" type="submit">Subscribe</button>
    </form>
  </div>
</section>

<footer>
  <div class="container">
    <div class="footer-grid">
      <div>
        <div class="footer-brand">URBAN<span>THREADS</span></div>
        <p class="footer-tag">Premium, data-informed personalized apparel. Built for the streets. Worn in the boardroom.</p>
      </div>
      <div>
        <p class="fc-title">Shop</p>
        <ul class="fc-links">
          <li><a href="#">New Arrivals</a></li><li><a href="#">Hoodies</a></li>
          <li><a href="#">Outerwear</a></li><li><a href="#">Denim</a></li><li><a href="#">Sale</a></li>
        </ul>
      </div>
      <div>
        <p class="fc-title">Company</p>
        <ul class="fc-links">
          <li><a href="#">About Us</a></li><li><a href="#">Lookbook</a></li>
          <li><a href="#">Sustainability</a></li><li><a href="#">Careers</a></li>
        </ul>
      </div>
      <div>
        <p class="fc-title">Support</p>
        <ul class="fc-links">
          <li><a href="#">FAQ</a></li><li><a href="#">Shipping</a></li>
          <li><a href="#">Size Guide</a></li><li><a href="#">Contact</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p class="footer-legal">&copy; 2026 Urban Threads -- <a href="#">Privacy</a> -- <a href="#">Terms</a></p>
      <p class="footer-legal">Instagram -- TikTok -- Pinterest</p>
    </div>
  </div>
</footer>

</body></html>"""


# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@router.post("/generate")
async def generate_campaign(req: CampaignRequest):
    """
    Main campaign generation endpoint.
    Returns JSON with email_html, landing_page_html, copy, and metadata.
    Called by the AgenticFlow Dashboard frontend.
    """
    import traceback
    try:
        return await _generate_campaign_inner(req)
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

async def _generate_campaign_inner(req: CampaignRequest):
    import traceback, sys
    print(f"[CAMPAIGN] Starting for {req.company}", flush=True)
    print(f"[CAMPAIGN] SKUs: {req.selected_skus}", flush=True)
    print(f"[CAMPAIGN] Token: {bool(req.directus_token)}", flush=True)
    products = await fetch_products(req.selected_skus, token=req.directus_token, url=req.directus_url)
    print(f"[CAMPAIGN] Products fetched: {len(products)}", flush=True)

    # Segment-aware product filtering fallback
    if not products:
        seg_cats = SEGMENT_CONFIG.get(req.segment, SEGMENT_CONFIG["default"])["categories"]
        all_products = await fetch_products(token=req.directus_token, url=req.directus_url)
        products = [p for p in all_products if p.get("category") in seg_cats][:4]

    print("[GEN] step 1: pick_hero", flush=True)
    hero_url = pick_hero(req.segment, req.hero_image_key)
    print(f"[GEN] step 1b: hero_url={hero_url[:40]}", flush=True)
    print(f"[GEN] step 2: generate_copy products={len(products)}", flush=True)
    try:
        copy = await generate_copy_with_ai(req, products)
        print(f"[GEN] step 2b: copy OK keys={list(copy.keys())}", flush=True)
    except Exception as ce:
        print(f"[GEN] step 2 CRASHED: {ce}", flush=True)
        import traceback; traceback.print_exc()
        raise
    print(f"[GEN] step 3: generate_email copy_keys={list(copy.keys()) if copy else None}", flush=True)
    email_html = generate_email_html(req, copy, products, hero_url)
    print("[GEN] step 4: generate_lp", flush=True)
    lp_html    = generate_landing_page_html(req, copy, products)
    print("[GEN] step 5: done", flush=True)

    return {
        "status":             "success",
        "company":            req.company,
        "segment":            req.segment,
        "variant":            req.variant,
        "abm_score":          req.abm_score,
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "copy":               copy,
        "hero_url":           hero_url,
        "products_used":      [{"sku": p.get("sku"), "name": p.get("name"), "price": p.get("price")} for p in products],
        "email_html":         email_html,
        "landing_page_html":  lp_html,
    }


@router.post("/generate/email", response_class=HTMLResponse)
async def download_email(req: CampaignRequest):
    """Returns raw HTML email --- downloadable directly from browser."""
    products = await fetch_products(req.selected_skus, token=req.directus_token, url=req.directus_url) or await fetch_products()
    hero_url = pick_hero(req.segment, req.hero_image_key)
    copy     = await generate_copy_with_ai(req, products)
    html     = generate_email_html(req, copy, products, hero_url)
    slug     = req.company.lower().replace(" ", "-")
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="ut_{slug}_email.html"'}
    )


@router.post("/generate/landing-page", response_class=HTMLResponse)
async def download_landing_page(req: CampaignRequest):
    """Returns raw HTML landing page --- downloadable directly from browser."""
    products = await fetch_products(req.selected_skus, token=req.directus_token, url=req.directus_url) or await fetch_products()
    copy     = await generate_copy_with_ai(req, products)
    html     = generate_landing_page_html(req, copy, products)
    slug     = req.company.lower().replace(" ", "-")
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="ut_{slug}_landing.html"'}
    )


@router.post("/generate/ab-test")
async def generate_ab_test(req: CampaignRequest):
    """
    Generate two campaign variants (A/B) in one call.
    Variant A = original tone, Variant B = alternative tone.
    """
    tones = {"Confident": "Urgent", "Premium": "Playful", "Playful": "Premium", "Urgent": "Exclusive", "Exclusive": "Confident"}
    alt_tone = tones.get(req.tone, "Premium")

    req_b         = req.model_copy()
    req_b.tone    = alt_tone
    req_b.variant = "B"

    products = await fetch_products(req.selected_skus, token=req.directus_token, url=req.directus_url) or await fetch_products()
    hero_url = pick_hero(req.segment, req.hero_image_key)

    copy_a = await generate_copy_with_ai(req, products)
    copy_b = await generate_copy_with_ai(req_b, products)

    req.variant   = "A"
    email_a = generate_email_html(req, copy_a, products, hero_url)
    email_b = generate_email_html(req_b, copy_b, products, hero_url)
    lp_a    = generate_landing_page_html(req, copy_a, products)
    lp_b    = generate_landing_page_html(req_b, copy_b, products)

    return {
        "status":    "success",
        "company":   req.company,
        "variant_a": {"tone": req.tone,  "copy": copy_a, "email_html": email_a, "landing_page_html": lp_a},
        "variant_b": {"tone": alt_tone,  "copy": copy_b, "email_html": email_b, "landing_page_html": lp_b},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "html-campaign-generator", "version": "2.0.0"}
