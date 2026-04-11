"""
pxm_campaign_routes.py
────────────────────────────────────────────────────────────────────────────────
PXM Campaign Studio — Unified endpoint
Merges: CRM (WHO) + PIM (WHY) + DAM (LOOK) + AI (SYNTHESIZE) → Full Campaign

POST /pxm/campaign/generate
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import httpx, os, json, time, re

router = APIRouter(prefix="/pxm", tags=["PXM Campaign Studio"])

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL       = "https://pim-dam-crm-integration-production.up.railway.app"
DIRECTUS_URL   = os.getenv("DIRECTUS_URL", "https://directus-production-9f53.up.railway.app")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
OPENAI_KEY     = os.getenv("OPENAI_API_KEY", "")


# ── Scenario → hero SKU for Printful mockup ───────────────────────────────────
SCENARIO_SKU_MAP = {
    "onboarding": "HOD-001",
    "events":     "ACC-001",
    "gifting":    "HOD-002",
}

# ── Hero image map (Cloudinary DAM) ──────────────────────────────────────────
HERO_IMAGES = {
    "tech_event":         "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853363/techevent_bope9u.png",
    "quiet_wealth":       "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853363/quietwealth_wtessy.png",
    "serious_purpose":    "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853362/seriouspurpose_riagvs.png",
    "campus_crew":        "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853361/campuscrew_eemlmd.png",
    "professional_pride": "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853360/professionalpride_v8bt3b.png",
    "power_performance":  "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853359/powerandperformance_bkhluo.png",
    "late_chemistry":     "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853359/latechemistry_w9zdf8.png",
    "pool_party":         "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775853357/companypoolparty_jgqxdf.png",
    "default":            "https://res.cloudinary.com/dp0cdq8bj/image/upload/q_auto/f_auto/v1775588160/image-img_01knmmr0tnfqdbscgy8jncxk04_doms3d.png",
}



# ── Industry → best-fit scenario ─────────────────────────────────────────────
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
    "Adventure Travel":         "events",
}



# ── Request model ─────────────────────────────────────────────────────────────
class PXMCampaignRequest(BaseModel):
    company_name: str
    scenario:     Optional[str] = None
    tone:         Optional[str] = "confident"
    hero_key:     Optional[str] = "default"   # ← add back

# ── Helpers ───────────────────────────────────────────────────────────────────

async def fetch_crm_account(company_name: str) -> dict:
    """Pull account data from ACCOUNTS list, with fallback."""
    from accounts import ACCOUNTS
    name_lower = company_name.strip().lower()
    for acc in ACCOUNTS:
        if acc.get("company_name", "").lower() == name_lower:
            return {
                "company":        acc["company_name"],
                "industry":       acc["industry"],
                "segment":        acc.get("use_case", ""),
                "pain_point":     acc.get("pain_point", ""),
                "use_case":       acc.get("use_case", ""),
                "buying_stage":   acc.get("buying_stage", ""),
                "company_size":   acc.get("company_size", ""),
                "employees":      acc.get("employees", ""),
                "annual_revenue": acc.get("annual_revenue", ""),
                "account_value":  acc.get("account_value", ""),
                "contact_name":   acc["contact"]["name"],
                "contact_title":  acc["contact"]["title"],
                "interested_categories": acc.get("interested_categories", []),
            }
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
    """Get Printful mockup URL from existing endpoint."""
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
- Buying Stage: {account.get('stage', account.get('buying_stage', '—'))}
- Pain Point:   {account.get('pain_point', '—')}
- Use Case:     {account.get('use_case', '—')}
- Contact:      {account.get('contact_name', '—')}, {account.get('contact_title', '—')}
- Employees:    {account.get('employees', '—')}
- Revenue:      {account.get('annual_revenue', '—')}
"""


def format_pxm_products_for_prompt(products: list) -> str:
    if not products:
        return "No products available."
    lines = []
    for p in products[:6]:
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
5. Hero image URL — an AI-generated contextual lifestyle photo matching the customer's industry

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
  → ALL CAPS, wide letter-spacing (2–4px), hero headlines, section titles, logotype
  → Load via: <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
- Subheadings / labels / product names:  'Open Sans', Tahoma, sans-serif — font-weight 700
- Body copy / fine print:  'Open Sans', Tahoma, sans-serif — font-weight 400, line-height 1.7

LOGOTYPE — render as styled TEXT only, never an <img> tag:
- Dark backgrounds: <span style="font-family:'Bebas Neue',Impact,sans-serif; font-size:28px; letter-spacing:4px; color:#D4AF37;">URBAN THREADS</span>
- Light backgrounds: same but color:#191714
- Keep compact: 28px max in headers/footers

NO TEXTURE IMAGES — gradients and vignettes only over photos.

═══════════════════════════════════════
EMAIL HTML DESIGN REQUIREMENTS
═══════════════════════════════════════
Build a complete, production-quality HTML email (600px max-width, inline styles).
Import Bebas Neue + Open Sans from Google Fonts in <head>.

STRUCTURE:
1. HEADER — #191714 bg, URBAN THREADS logotype left (Bebas Neue 28px #D4AF37), 2px #D4AF37 bottom border
2. HERO — background-image: HERO IMAGE URL, cover center, min-height 280px
   overlay: linear-gradient(to bottom, rgba(25,23,20,0.45), rgba(25,23,20,0.75))
   Headline: Bebas Neue 52px #F5F0E8 ALL CAPS, Subhead: Open Sans 700 16px #D4AF37
3. INTRO — #F5F0E8 bg, "Hi [Contact Name]," Bebas Neue 22px #191714, body Open Sans 14px #191714
   left border 3px #D4AF37
4. PRODUCT CARDS — #191714 bg, left bar 4px #D4AF37
   Name: Open Sans 700 18px #D4AF37, Reason: Open Sans 13px #F5F0E8, Note: Open Sans 600 13px #C4A882
5. BUNDLE — #D4AF37 bg, name Bebas Neue 30px #191714, SKUs Open Sans 12px #4E511E
   CTA button: #191714 bg, #D4AF37 text, Bebas Neue 18px, padding 12px 36px
6. FOOTER — #4E511E bg, URBAN THREADS logotype Bebas Neue 22px #F5F0E8
   Tagline: Open Sans italic 13px #C4A882 "Premium Apparel. Precision Marketing."

═══════════════════════════════════════
LANDING PAGE HTML DESIGN REQUIREMENTS
═══════════════════════════════════════
Build a complete, modern HTML landing page (full-width, internal <style> block).
Import Bebas Neue + Open Sans from Google Fonts in <head>.

STRUCTURE:
1. NAV — #191714 bg 60px, URBAN THREADS logotype left Bebas Neue 26px #D4AF37
   CTA button right: #D4AF37 bg, #191714 text, Bebas Neue 16px
2. HERO — full-width min-height 560px, background-image: HERO IMAGE URL cover center
   overlay: linear-gradient(135deg, rgba(25,23,20,0.80), rgba(25,23,20,0.40) 60%, rgba(25,23,20,0.65))
   H1: Bebas Neue 88px #F5F0E8 letter-spacing 5px ALL CAPS
   H2: Open Sans 700 22px #D4AF37
   CTA: #D4AF37 bg, #191714 text, Bebas Neue 22px, padding 14px 48px
3. PERSONALIZATION BAND — #D4AF37 bg, Open Sans 700 13px #191714
   "Crafted exclusively for [Company] · [Industry] · [Contact Name], [Title]"
4. VALUE PROPS — #F5F0E8 bg, 3 columns: emoji icon, Bebas Neue 20px #191714 label,
   Open Sans 13px #4E511E description (⚡ Rapid Production / 🎨 Custom Branding / ✦ Premium Quality)
5. PRODUCTS — #191714 bg, header Bebas Neue 52px #F5F0E8, gold underline
   Cards: #F5F0E8 bg, SKU badge #4E511E bg #C4A882 text, name Open Sans 700 20px #191714,
   reason Open Sans 13px, personalization note Open Sans 600 13px #D4AF37
6. BUNDLE — #4E511E bg, name Bebas Neue 60px #D4AF37 letter-spacing 4px
   SKU pills #191714 bg #C4A882 text, CTA #D4AF37 bg #191714 text Bebas Neue 24px
7. STATS — #191714 bg border-top 3px #D4AF37, 3 stats Bebas Neue 44px #D4AF37
   labels Open Sans 12px #C4A882: "500+ Brands Outfitted" · "48-Hour Rush Available" · "MOQ from 12 Units"
8. FINAL CTA — #F5F0E8 bg, headline Bebas Neue 56px #191714, subtext Open Sans 19px #4E511E
   button #D4AF37 bg #191714 text Bebas Neue 22px
9. FOOTER — #4E511E bg, URBAN THREADS Bebas Neue 24px #F5F0E8
   Tagline Open Sans 14px italic #C4A882 "Premium Apparel. Precision Marketing."

═══════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════
{
  "campaign_title": "max 8 words",
  "subject_line": "personalized, max 10 words",
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
  "email_html": "<FULL production-quality HTML email>",
  "landing_page_html": "<FULL production-quality HTML landing page>"
}

RULES:
- Always open email with "Hi [contact_name]," using actual first name from CRM
- Always reference company name AND industry in body_copy
- Match products precisely to pain_point and use_case
- The HERO IMAGE URL passed in the user message is an AI-generated scene — use it as hero background in both email and landing page
- CSS gradients/vignettes over hero image only — NO texture background-images
- Render brand name as Bebas Neue TEXT logotype — NEVER use <img> for logo
- email_html and landing_page_html must be complete self-contained HTML documents
- NO external CSS frameworks — inline styles for email, internal <style> for landing page
- Return ONLY valid JSON. No markdown, no explanation, no code fences.
"""

# ── Main endpoint ─────────────────────────────────────────────────────────────
@router.post("/campaign/generate")
async def generate_pxm_campaign(req: PXMCampaignRequest):
    """
    PXM Campaign Studio — Unified generation endpoint.
    WHO (CRM) + WHY (PIM) + LOOK (AI-generated DAM) + AI = Full Campaign + Mockup
    """
    start_ms = int(time.time() * 1000)

    # 1. Pull CRM account data
    account = await fetch_crm_account(req.company_name)

    # 2. Determine scenario
    scenario = req.scenario or INDUSTRY_SCENARIO_MAP.get(
        account.get("industry", ""), "onboarding"
    )

    # 3. Pull PXM-enriched products filtered for scenario
    products = await fetch_pxm_products(scenario)

    # 4. Fetch Printful mockup + resolve hero image from DAM
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

══════════════════════════════════════════
HERO IMAGE — YOU MUST USE THIS EXACT URL
══════════════════════════════════════════
{hero_image}

This URL MUST appear as the background-image in BOTH the email hero section AND
the landing page hero section. Do not use any other image URL. Do not use a
placeholder. Copy this URL exactly as written above.
══════════════════════════════════════════

Generate the full PXM campaign JSON now.
Apply gradient overlays only over the hero image — no textures.
Render the brand logotype as Bebas Neue text — no image tags for the logo.
"""

    # 6. Call GPT-4o (single call)
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

    # DIAGNOSTIC — remove after fix confirmed
    print(f"DEBUG hero_key received: {req.hero_key}")
    print(f"DEBUG hero_image resolved: {hero_image}")
    print(f"DEBUG email_html contains hero_image: {hero_image in brief.get('email_html', '')}")
    print(f"DEBUG email_html cloudinary URLs: {re.findall(r'https://res\.cloudinary\.com/dp0cdq8bj/image/upload/[^\s\'\")\]]+', brief.get('email_html', ''))}")

    # ── Force correct hero URL — replace ANY Cloudinary URL in background-image ──
    # GPT ignores the URL we pass and always uses a hardcoded one. We fix it here.
    for field in ("email_html", "landing_page_html"):
        html = brief.get(field, "")
        if isinstance(html, str) and hero_image:
            # Replace all Cloudinary URLs unconditionally — hero is always a background-image
            brief[field] = re.sub(
                r'https://res\.cloudinary\.com/dp0cdq8bj/image/upload/[^\s\'")\]]+',
                hero_image,
                html
            )

    latency_ms = int(time.time() * 1000) - start_ms

    # 7. Return unified response
    return {
        "status":             "success",
        "scenario":           scenario,
        "tone":               req.tone,
        "account":            account,
        "products_evaluated": len(products),
        "campaign_brief":     brief,
        "mockup_url":         mockup_url,
        "mockup_sku":         hero_sku,
        "hero_image_url":     hero_image,
        "model":              response.model,
        "tokens_used":        response.usage.total_tokens,
        "latency_ms":         latency_ms,
    }