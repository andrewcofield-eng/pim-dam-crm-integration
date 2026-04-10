"""
pxm_campaign_routes.py
─────────────────────────────────────────────────────────────────────────────
PXM Campaign Studio — Unified endpoint
Merges: CRM (WHO) + PIM (WHY) + DAM (LOOK) + AI (SYNTHESIZE) → Full Campaign

POST /pxm/campaign/generate
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import httpx, os, json, time

router = APIRouter(prefix="/pxm", tags=["PXM Campaign Studio"])

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL       = "https://pim-dam-crm-integration-production.up.railway.app"
DIRECTUS_URL   = os.getenv("DIRECTUS_URL", "https://directus-production-9f53.up.railway.app")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
OPENAI_KEY     = os.getenv("OPENAI_API_KEY", "")

# ── Hero image map (Cloudinary DAM) ───────────────────────────────────────────
HERO_IMAGES = {
    "default":       "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774727348/HOD-001_ACC_001City_street_heelsWoman_w18vkt.png",
    "rooftop_couple":"https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774727354/HOD-001_ACC_001Rooftopcouple_oh5qrh.png",
    "wall_woman":    "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774727359/HOD-001_ACC_001wallWoman_a0mjrd.png",
    "car_couple":    "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774727347/HOD-001_ACC_001carhoodcouple_jboayc.png",
    "rooftop_man":   "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774727352/HOD-001_ACC_001Rooftop_man_thivq3.png",
    "coffee_man":    "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774727363/KNIT-001coffeeshopMan_rvhsik.png",
}

# Scenario → hero SKU for Printful mockup
SCENARIO_SKU_MAP = {
    "onboarding": "HOD-001",
    "events":     "ACC-001",
    "gifting":    "HOD-002",
}

# Industry → best-fit scenario (fallback if not specified)
INDUSTRY_SCENARIO_MAP = {
    "Fitness Chain":            "onboarding",
    "Corporate Merchandise":    "gifting",
    "Event Management":         "events",
    "College Merchandise":      "events",
    "Employee Benefits":        "onboarding",
    "Hospitality":              "gifting",
    "Outdoor Apparel Retail":   "events",
    "Fashion Retail":           "onboarding",
    "Non-Profit":               "onboarding",
}

# ── Request model ─────────────────────────────────────────────────────────────
class PXMCampaignRequest(BaseModel):
    company_name: str
    scenario:     Optional[str] = None      # onboarding | events | gifting
    tone:         Optional[str] = "confident"
    hero_key:     Optional[str] = "default"

# ── Helpers ───────────────────────────────────────────────────────────────────

async def fetch_crm_account(company_name: str) -> dict:
    """Pull account data — first try ACCOUNTS list, then ABM endpoint as fallback."""
    from accounts import ACCOUNTS

    # Direct lookup from ACCOUNTS (same source as HubSpot orchestrator)
    name_lower = company_name.strip().lower()
    for acc in ACCOUNTS:
        if acc.get("company_name", "").lower() == name_lower:
            return {
                "company":       acc["company_name"],
                "industry":      acc["industry"],
                "segment":       acc.get("use_case", ""),
                "pain_point":    acc.get("pain_point", ""),
                "use_case":      acc.get("use_case", ""),
                "buying_stage":  acc.get("buying_stage", ""),
                "company_size":  acc.get("company_size", ""),
                "employees":     acc.get("employees", ""),
                "annual_revenue":acc.get("annual_revenue", ""),
                "account_value": acc.get("account_value", ""),
                "contact_name":  acc["contact"]["name"],
                "contact_title": acc["contact"]["title"],
                "interested_categories": acc.get("interested_categories", []),
            }

    # Fallback
    return {"company": company_name, "industry": "General B2B", "segment": "general"}

async def fetch_pxm_products(scenario: str) -> list:
    """Pull PIM products enriched with WHY data, filtered by scenario."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{BASE_URL}/products/export?scenario={scenario}", timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json().get("products", [])
    except Exception:
        pass
    return []


async def fetch_mockup(company_name: str, sku: str) -> Optional[str]:
    """Get Printful mockup URL from your existing endpoint."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{BASE_URL}/printful-mockups/generate",
                json={"company_name": company_name, "sku": sku},
            )
            if resp.status_code == 200:
                return resp.json().get("mockup_url")
    except Exception:
        pass
    return None


def format_crm_for_prompt(account: dict) -> str:
    return f"""
CRM ACCOUNT (WHO):
- Company:      {account.get('company', account.get('company_name', 'Unknown'))}
- Industry:     {account.get('industry', '—')}
- Segment:      {account.get('segment', '—')}
- Deal Value:   {account.get('deal_value', '—')}
- ABM Score:    {account.get('abm_score', '—')}
- Buying Stage: {account.get('stage', account.get('buying_stage', '—'))}
- Pain Point:   {account.get('pain_point', '—')}
- Use Case:     {account.get('use_case', '—')}
- Contact:      {account.get('contact_name', account.get('contact', {}).get('name', '—'))}
"""


def format_pxm_products_for_prompt(products: list) -> str:
    if not products:
        return "No products available."
    lines = []
    for p in products[:6]:  # cap at 6 for prompt size
        scores = p.get("scenario_scores", {})
        merch  = p.get("merchandising", {})
        fit    = p.get("marketing_fit", {})
        lines.append(
            f"SKU: {p.get('sku')} | {p.get('name')} | ${p.get('price')}\n"
            f"  WHY — Solves: {', '.join(fit.get('ideal_audience', []))}\n"
            f"  Vertical Fit: {', '.join(fit.get('vertical_fit', []))}\n"
            f"  Bundle Role: {merch.get('bundle_role')} | Value Tier: {merch.get('value_tier')}\n"
            f"  Scenario Scores → Onboarding: {scores.get('onboarding')} | "
            f"Events: {scores.get('events')} | Gifting: {scores.get('gifting')}"
        )
    return "\n\n".join(lines)


# ── System prompt ─────────────────────────────────────────────────────────────
# ── Brand Asset Library (Cloudinary DAM) ─────────────────────────────────────
# ── Brand Asset Library (Cloudinary DAM) ─────────────────────────────────────
URBAN_THREADS_BRAND = {
    "logo_dark_bg":  "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774714664/urbanthreads-PrimaryLogo-DKbkgrd_dbzktr.png",
    "logo_light_bg": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774714662/urbanthreads-PrimaryLogo-LTbkgrd_q1hdpt.png",
    "texture_1":     "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774728063/image-img_01kmtgh0jtey4sgqqky0hjc0zh_cshocs.jpg",
    "texture_2":     "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774728062/image-img_01kmtghapbf2hrqbv9ajx2zt5b_amokq5.jpg",
    "colors": {
        "black":      "#191714",   # primary background, text
        "cream":      "#F5F0E8",   # light background, body text on dark
        "gold":       "#D4AF37",   # primary accent, CTAs, borders
        "tan":        "#C4A882",   # secondary accent, muted highlights
        "olive":      "#4E511E",   # tertiary accent, footer, badges
    },
    "fonts": {
        "display":    "'Bebas Neue', Impact, sans-serif",       # hero headlines, campaign titles
        "editorial":  "Garamond, 'Times New Roman', serif",     # subheadings, pull quotes
        "body":       "Verdana, Geneva, sans-serif",            # body copy, labels, meta
    }
}

PXM_SYSTEM_PROMPT = """
You are an expert B2B marketing strategist and senior email designer for AgenticFlow — a marketing technology agency.

Your client is Urban Threads, a premium promotional apparel brand serving both B2C and B2B markets.
Urban Threads sells customized branded clothing and accessories to businesses needing corporate swag,
event merchandise, employee uniforms, and gifting programs.

You operate at the intersection of PXM (Product Experience Management) and CRM intelligence.
Your job: synthesize CRM account signals (WHO) with PIM product intelligence (WHY) to generate
a precisely targeted, personalized campaign that connects the right product to the right customer.

You will receive:
1. CRM data — company profile, industry, pain points, buying stage, contact name & title
2. PXM product data — products enriched with WHY (scenario fit, vertical fit, bundle role, value tier)
3. Campaign scenario: onboarding | events | gifting
4. Tone: confident | urgent | premium | playful | exclusive
5. Hero image URL — a lifestyle photo from the Urban Threads DAM (Cloudinary)

═══════════════════════════════════════════════════════
URBAN THREADS BRAND IDENTITY (ALWAYS USE THESE ASSETS)
═══════════════════════════════════════════════════════

COLORS — use ONLY these hex values:
- #191714  — Charcoal Black   → primary backgrounds, heavy text
- #F5F0E8  — Warm Cream       → light section backgrounds, body text on dark
- #D4AF37  — Antique Gold     → CTAs, borders, accent headlines, buttons
- #C4A882  — Desert Tan       → secondary accents, muted labels, dividers
- #4E511E  — Olive Dark       → footer backgrounds, badge backgrounds, tertiary elements

TYPOGRAPHY — use ONLY these font stacks:
- Display / Hero Headlines:  'Bebas Neue', Impact, sans-serif
  → Use for: campaign title, hero headline, section headers — ALL CAPS, wide letter-spacing
  → Load via: <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap" rel="stylesheet">
- Editorial / Subheadings:   Garamond, 'Times New Roman', serif
  → Use for: subheadings, pull quotes, product names, personalization notes — elegant, italic where appropriate
- Body / Labels / Meta:      Verdana, Geneva, sans-serif
  → Use for: body copy, bullet points, fine print, meta data — small, readable

LOGO ASSETS (pull directly from Cloudinary DAM):
- On dark/black backgrounds:  https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774714664/urbanthreads-PrimaryLogo-DKbkgrd_dbzktr.png
- On light/cream backgrounds: https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774714662/urbanthreads-PrimaryLogo-LTbkgrd_q1hdpt.png

TEXTURE ASSETS (use as background-image with overlay for richness):
- Texture 1: https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774728063/image-img_01kmtgh0jtey4sgqqky0hjc0zh_cshocs.jpg
- Texture 2: https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774728062/image-img_01kmtghapbf2hrqbv9ajx2zt5b_amokq5.jpg

═══════════════════════════════════════
EMAIL HTML DESIGN REQUIREMENTS
═══════════════════════════════════════
Build a complete, production-quality HTML email (600px max-width, inline styles for email client compatibility).
Import Bebas Neue from Google Fonts in the <head>.

STRUCTURE:
1. HEADER
   - Background: #191714
   - Urban Threads logo (dark bg version), centered, padding 24px
   - 3px gold (#D4AF37) bottom border

2. HERO SECTION
   - Background-image: the provided HERO IMAGE URL, cover, center
   - Dark overlay: rgba(25,23,20,0.55)
   - Hero headline: Bebas Neue, 48px, white, letter-spacing 3px, ALL CAPS
   - Subheading: Garamond italic, 18px, #D4AF37

3. PERSONALIZED INTRO
   - Background: #F5F0E8
   - Opening: "Hi [Contact Name]," in Bebas Neue 22px #191714
   - Body copy: Verdana 14px #191714, line-height 1.7
   - Left border accent: 3px solid #D4AF37

4. PRODUCT RECOMMENDATION CARDS (1 card per product)
   - Background: #191714, border: 1px solid #C4A882, border-radius 4px
   - Product name: Garamond bold italic, 20px, #D4AF37
   - Reason copy: Verdana 13px, #F5F0E8
   - Personalization note: Garamond italic, 13px, #C4A882
   - Left accent bar: 4px solid #D4AF37

5. BUNDLE HIGHLIGHT
   - Background: #D4AF37
   - Bundle name: Bebas Neue 28px, #191714, letter-spacing 2px
   - SKU list: Verdana 12px, #4E511E
   - CTA button: #191714 background, #D4AF37 text, Bebas Neue 18px, padding 12px 32px

6. TEXTURE ACCENT STRIP
   - background-image: Texture 1 URL, height 60px, background-size cover
   - overlay: rgba(25,23,20,0.6)

7. FOOTER
   - Background: #4E511E
   - Urban Threads logo (light bg version — use on this olive background)
   - Verdana 11px, #C4A882 text
   - Tagline: "Premium Apparel. Precision Marketing." in Garamond italic #F5F0E8

═══════════════════════════════════════
LANDING PAGE HTML DESIGN REQUIREMENTS
═══════════════════════════════════════
Build a complete, modern HTML landing page (full-width, CSS grid/flexbox, internal <style> block).
Import Bebas Neue from Google Fonts in the <head>.

STRUCTURE:
1. NAV BAR
   - Background: #191714, height 64px
   - Urban Threads logo (dark bg version) left-aligned
   - Right: gold CTA button — Bebas Neue, #D4AF37 background, #191714 text

2. HERO SECTION
   - Full-width, min-height 540px
   - background-image: the provided HERO IMAGE URL + Texture 2 at 8% opacity overlay
   - Dark gradient overlay: linear-gradient(rgba(25,23,20,0.7), rgba(25,23,20,0.5))
   - H1: Bebas Neue 80px, #F5F0E8, letter-spacing 4px, ALL CAPS
   - H2 subheading: Garamond italic 24px, #D4AF37
   - CTA button: #D4AF37 background, #191714 text, Bebas Neue 20px

3. PERSONALIZATION BAND
   - Background: #D4AF37, padding 16px
   - Text: Verdana 13px, #191714, bold
   - Content: "Crafted exclusively for [Company] · [Industry] · [Contact Name], [Title]"

4. VALUE PROPS — 3 columns
   - Background: #F5F0E8
   - Icon (use emoji: ⚡ 🎨 ✦), Bebas Neue 18px label #191714, Verdana 13px description #4E511E

5. PRODUCT SHOWCASE
   - Background: #191714
   - Section header: Bebas Neue 48px #F5F0E8, gold underline
   - Product cards: #F5F0E8 background, Garamond bold 20px product name in #191714,
     Verdana 13px reason, #D4AF37 personalization note, olive (#4E511E) SKU badge

6. BUNDLE SECTION
   - background-image: Texture 1, with rgba(25,23,20,0.8) overlay
   - Bundle name: Bebas Neue 56px, #D4AF37, letter-spacing 3px
   - SKU pills: #4E511E background, #C4A882 text
   - CTA button: #D4AF37 background, #191714 text, large

7. STATS BAND
   - Background: #2A2720 (near-black)
   - 3 stats in Bebas Neue 36px #D4AF37 with Verdana 12px #C4A882 labels
   - "500+ Brands Outfitted" · "48-Hour Rush Available" · "MOQ from 12 Units"

8. FINAL CTA
   - Background: #191714
   - Headline: Bebas Neue 52px #F5F0E8
   - Subtext: Garamond italic 18px #C4A882, tied to the scenario pain point
   - Button: #D4AF37, Bebas Neue, large, hover effect

9. FOOTER
   - Background: #4E511E
   - Logo: light bg version
   - Tagline: Garamond italic, #F5F0E8, "Premium Apparel. Precision Marketing."
   - Verdana 11px #C4A882 fine print

═══════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════
Output a single valid JSON object with these exact keys:
{
  "campaign_title": "max 8 words",
  "subject_line": "personalized email subject, max 10 words",
  "hero_headline": "benefit-driven, max 12 words, ALL CAPS friendly",
  "body_copy": "2-3 sentences referencing company name, industry, and pain point",
  "product_recommendations": [
    {
      "sku": "...",
      "name": "...",
      "reason": "1 sentence — why THIS product for THIS company",
      "personalization_note": "how to personalize for this account"
    }
  ],
  "bundle_suggestion": { "name": "...", "skus": ["..."] },
  "cta_text": "max 6 words",
  "personalization_angle": "1-2 sentences on persona-specific angle for the contact",
  "campaign_notes": "strategic notes on timing, MOQ, vertical considerations",
  "email_html": "<FULL production-quality HTML email per EMAIL requirements above>",
  "landing_page_html": "<FULL production-quality HTML landing page per LANDING PAGE requirements above>"
}

RULES:
- Always open the email with "Hi [contact_name]," using the actual contact name from CRM data
- Always reference the company name AND industry in body_copy
- Match products precisely to the account's pain_point and use_case
- Use the EXACT Cloudinary asset URLs above — never use placeholder or external images
- The HERO IMAGE URL passed in the user message MUST be the email and landing page hero background
- email_html and landing_page_html must be complete, self-contained HTML documents
- NO external CSS frameworks — inline styles for email, internal <style> block for landing page
- Return ONLY valid JSON. No markdown, no explanation, no code fences.
"""

# ── Main endpoint ─────────────────────────────────────────────────────────────
@router.post("/campaign/generate")
async def generate_pxm_campaign(req: PXMCampaignRequest):
    """
    PXM Campaign Studio — Unified generation endpoint.
    WHO (CRM) + WHY (PIM) + LOOK (DAM) + AI = Full Campaign + Mockup
    """
    start_ms = int(time.time() * 1000)

    # 1. Pull CRM account data
    account = await fetch_crm_account(req.company_name)

    # 2. Determine scenario (use provided or infer from industry)
    scenario = req.scenario or INDUSTRY_SCENARIO_MAP.get(
        account.get("industry", ""), "onboarding"
    )

    # 3. Pull PXM-enriched products filtered for scenario
    products = await fetch_pxm_products(scenario)

    # 4. Fetch Printful mockup + hero image in parallel
    hero_sku   = SCENARIO_SKU_MAP.get(scenario, "HOD-001")
    hero_image = HERO_IMAGES.get(req.hero_key or "default", HERO_IMAGES["default"])

    mockup_url = await fetch_mockup(req.company_name, hero_sku)

    # 5. Build prompt context
    crm_context = format_crm_for_prompt(account)
    pxm_context = format_pxm_products_for_prompt(products)

    user_message = f"""
{crm_context}

PXM PRODUCTS (WHY — what each product solves):
{pxm_context}

CAMPAIGN SCENARIO: {scenario.upper()}
TONE: {req.tone or 'confident'}
HERO IMAGE URL: {hero_image}

BRAND ASSETS AVAILABLE IN DAM:
- Logo (dark bg): {URBAN_THREADS_BRAND['logo_dark_bg']}
- Logo (light bg): {URBAN_THREADS_BRAND['logo_light_bg']}
- Texture 1: {URBAN_THREADS_BRAND['texture_1']}
- Texture 2: {URBAN_THREADS_BRAND['texture_2']}

Generate the full PXM campaign JSON now. Use ALL brand assets in the HTML outputs.
"""

    # 6. Call GPT-4o
    client_ai = OpenAI(api_key=OPENAI_KEY)
    response  = client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PXM_SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    brief = json.loads(response.choices[0].message.content)
    latency_ms = int(time.time() * 1000) - start_ms

    # 7. Return unified response
    return {
        "status":      "success",
        "scenario":    scenario,
        "tone":        req.tone,
        "account":     account,
        "products_evaluated": len(products),
        "campaign_brief":     brief,
        "mockup_url":         mockup_url,
        "mockup_sku":         hero_sku,
        "hero_image_url":     hero_image,
        "model":       response.model,
        "tokens_used": response.usage.total_tokens,
        "latency_ms":  latency_ms,
    }