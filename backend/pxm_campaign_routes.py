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
# ── Brand Asset Library (Cloudinary DAM) ─────────────────────────────────────
URBAN_THREADS_BRAND = {
    "colors": {
        "black":  "#191714",
        "cream":  "#F5F0E8",
        "gold":   "#D4AF37",
        "tan":    "#C4A882",
        "olive":  "#4E511E",
    },
    "fonts": {
        "display":     "'Bebas Neue', Impact, sans-serif",   # headlines, logotype
        "subheading":  "'Open Sans', Tahoma, sans-serif",    # subheads, product names, labels — bold weight
        "body":        "'Open Sans', Tahoma, sans-serif",    # body copy, fine print — regular weight
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
URBAN THREADS BRAND IDENTITY
═══════════════════════════════════════════════════════

COLORS — use ONLY these hex values:
- #191714  Charcoal Black  → primary backgrounds, heavy text
- #F5F0E8  Warm Cream      → light section backgrounds, body text on dark
- #D4AF37  Antique Gold    → CTAs, borders, accent headlines, buttons
- #C4A882  Desert Tan      → secondary accents, muted labels, dividers
- #4E511E  Olive Dark      → footer backgrounds, badge backgrounds

TYPOGRAPHY:
- Display headlines:  'Bebas Neue', Impact, sans-serif
  → ALL CAPS, wide letter-spacing (2–4px), used for brand name logotype, hero headlines, section titles
  → Load via: <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">

- Subheadings / labels / product names:  'Open Sans', Tahoma, sans-serif — font-weight 700
  → Use wherever Garamond or Times New Roman was previously specified
  → No italic, no serif — clean, bold, modern

- Body copy / fine print / meta:  'Open Sans', Tahoma, sans-serif — font-weight 400
  → Use wherever Verdana was previously specified
  → Line-height 1.7–1.8, readable at 13–15px

LOGOTYPE — render the brand name as styled TEXT, not an image:
- Use: <span style="font-family:'Bebas Neue',Impact,sans-serif; font-size:28px; letter-spacing:4px; color:#D4AF37;">URBAN THREADS</span>
- On light/cream backgrounds use color #191714 instead of gold
- NEVER use an <img> tag for the logo — always render as Bebas Neue text
- Keep it compact: 28px in headers/footers, never larger

NO TEXTURE IMAGES — do not use any background-image textures.
All decorative styling over images must use CSS gradients or vignettes only.

═══════════════════════════════════════
EMAIL HTML DESIGN REQUIREMENTS
═══════════════════════════════════════
Build a complete, production-quality HTML email (600px max-width, inline styles for email client compatibility).
Import in <head>:
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">

STRUCTURE:

1. HEADER
   - Background: #191714
   - Left-aligned logotype: URBAN THREADS in Bebas Neue 28px, #D4AF37, letter-spacing 4px
   - Right-aligned: small label "Premium Apparel" in Verdana 10px, #C4A882
   - Bottom border: 2px solid #D4AF37
   - Padding: 16px 24px

2. HERO SECTION
   - Background-image: the provided HERO IMAGE URL, background-size: cover, background-position: center
   - Overlay: linear-gradient(to bottom, rgba(25,23,20,0.45) 0%, rgba(25,23,20,0.75) 100%)
   - Min-height: 280px, display flex, align-items center, justify-content center, text-align center
   - Hero headline: Bebas Neue 52px, #F5F0E8, letter-spacing 3px, ALL CAPS, text-shadow 0 2px 8px rgba(0,0,0,0.6)
   - Subheading: Gara'Open Sans', Tahoma, sans-serif; font-style:normal; font-weight:600mond italic 19px, #D4AF37, margin-top 8px

3. PERSONALIZED INTRO
   - Background: #F5F0E8
   - Padding: 28px 32px
   - Opening line: "Hi [Contact Name]," — Bebas Neue 22px, #191714, letter-spacing 1px
   - Body copy: Verdana 14px, #191714, line-height 1.8
   - Left accent border: 3px solid #D4AF37, padding-left 16px

4. PRODUCT CARDS (one per recommendation)
   - Background: #191714, border: 1px solid #C4A882, border-radius: 4px
   - Left accent bar: 4px solid #D4AF37
   - Product name: Open Sans', Tahoma, sans-serif; font-weight:700 20px, #D4AF37
   - Reason: Verdana 13px, #F5F0E8, line-height 1.6
   - Personalization note: 'Open Sans', Tahoma, sans-serif; font-style:normal; font-weight:600 13px, #C4A882
   - Padding: 16px 20px, margin-bottom 12px

5. BUNDLE HIGHLIGHT
   - Background: #D4AF37, padding 24px 32px
   - Bundle name: Bebas Neue 30px, #191714, letter-spacing 2px
   - SKU list: Verdana 12px, #4E511E
   - CTA button: background #191714, color #D4AF37, Bebas Neue 18px, padding 12px 36px,
     border-radius 2px, letter-spacing 2px, display inline-block, text-decoration none

6. FOOTER
   - Background: #4E511E, padding 20px 24px
   - Logotype: URBAN THREADS in Bebas Neue 22px, #F5F0E8, letter-spacing 3px
   - Tagline: Garamo'Open Sans', Tahoma, sans-serif; font-style:normal; font-weight:600nd italic 13px, #C4A882 — "Premium Apparel. Precision Marketing."
   - Fine print: Verdana 10px, #C4A882 — unsubscribe placeholder

═══════════════════════════════════════
LANDING PAGE HTML DESIGN REQUIREMENTS
═══════════════════════════════════════
Build a complete, modern HTML landing page (full-width, internal <style> block).
Import in <head>:
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">

STRUCTURE:

1. NAV BAR
   - Background: #191714, height 60px, padding 0 40px
   - Left: URBAN THREADS logotype — Bebas Neue 26px, #D4AF37, letter-spacing 4px
   - Right: CTA button — background #D4AF37, color #191714, Bebas Neue 16px, letter-spacing 1px,
     padding 8px 24px, border-radius 2px

2. HERO SECTION
   - Full-width, min-height 560px
   - background-image: the provided HERO IMAGE URL, background-size: cover, background-position: center
   - Overlay: linear-gradient(135deg, rgba(25,23,20,0.80) 0%, rgba(25,23,20,0.40) 60%, rgba(25,23,20,0.65) 100%)
   - Display: flex, flex-direction: column, align-items: center, justify-content: center, text-align: center
   - H1: Bebas Neue 88px, #F5F0E8, letter-spacing 5px, ALL CAPS, text-shadow 0 4px 16px rgba(0,0,0,0.5)
   - H2: Open Sans italic 26px, #D4AF37, margin-top 12px
   - CTA button: background #D4AF37, color #191714, Bebas Neue 22px, padding 14px 48px,
     letter-spacing 2px, border-radius 2px, margin-top 28px

3. PERSONALIZATION BAND
   - Background: #D4AF37, padding 14px 40px
   - Text: Verdana 13px bold, #191714, text-align center
   - Content: "Crafted exclusively for [Company] · [Industry] · [Contact Name], [Title]"

4. VALUE PROPS — 3 columns
   - Background: #F5F0E8, padding 60px 40px
   - Section title: Bebas Neue 42px, #191714, text-align center, margin-bottom 40px
   - Each column: emoji icon (⚡ 🎨 ✦), Bebas Neue 20px label #191714, Verdana 13px #4E511E description

5. PRODUCT SHOWCASE
   - Background: #191714, padding 60px 40px
   - Section header: Bebas Neue 52px, #F5F0E8, text-align center
   - Gold underline: 3px solid #D4AF37, width 60px, margin 12px auto 40px
   - Product cards: background #F5F0E8, border-radius 4px, padding 24px
     - SKU badge: background #4E511E, color #C4A882, Verdana 10px, letter-spacing 1px
     - Product name: Open Sans bold 20px, #191714
     - Reason: Verdana 13px, #191714, line-height 1.6
     - Personalization note: Open Sans italic 13px, #D4AF37

6. BUNDLE SECTION
   - Background: #4E511E, padding 60px 40px, text-align center
   - Bundle name: Bebas Neue 60px, #D4AF37, letter-spacing 4px
   - SKU pills: background #191714, color #C4A882, Verdana 11px, padding 4px 14px, border-radius 20px
   - CTA button: background #D4AF37, color #191714, Bebas Neue 24px, padding 16px 56px,
     border-radius 2px, margin-top 28px

7. STATS BAND
   - Background: #191714, padding 40px, border-top: 3px solid #D4AF37
   - 3 stats side by side — Bebas Neue 44px #D4AF37, Verdana 12px #C4A882 label below
   - "500+ Brands Outfitted" · "48-Hour Rush Available" · "MOQ from 12 Units"

8. FINAL CTA SECTION
   - Background: #F5F0E8, padding 80px 40px, text-align center
   - Headline: Bebas Neue 56px, #191714, letter-spacing 3px
   - Subtext: Open Sans italic 19px, #4E511E, tied to the scenario pain point
   - Button: background #D4AF37, color #191714, Bebas Neue 22px, padding 16px 52px,
     border-radius 2px, letter-spacing 2px

9. FOOTER
   - Background: #4E511E, padding 28px 40px
   - Logotype: URBAN THREADS — Bebas Neue 24px, #F5F0E8, letter-spacing 4px
   - Tagline: Open Sans italic 14px, #C4A882 — "Premium Apparel. Precision Marketing."
   - Fine print: Verdana 10px, #C4A882

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
- Always open the email with "Hi [contact_name]," using the actual first name from CRM data
- Always reference the company name AND industry in body_copy
- Match products precisely to the account's pain_point and use_case
- The HERO IMAGE URL passed in the user message MUST be the hero background in both email and landing page
- Use CSS gradients/vignettes over the hero image — NO texture background-images anywhere
- Render the brand name as Bebas Neue TEXT logotype only — NEVER use an <img> tag for the logo
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

Generate the full PXM campaign JSON now.
Use the hero image as the background for both email and landing page hero sections.
Apply gradient overlays only — no texture images.
Render the brand logotype as Bebas Neue text — no image tags for the logo.
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