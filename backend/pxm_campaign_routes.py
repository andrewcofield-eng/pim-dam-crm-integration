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
    """Pull live account data from HubSpot via your ABM endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/abm/warm-prospects")
            if resp.status_code == 200:
                prospects = resp.json().get("prospects", [])
                for p in prospects:
                    if p.get("company", "").lower() == company_name.lower():
                        return p
    except Exception:
        pass
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
PXM_SYSTEM_PROMPT = """
You are an expert B2B marketing strategist for Urban Threads, a premium promotional apparel brand.

You operate at the intersection of PXM (Product Experience Management) and CRM intelligence.

Your job: synthesize CRM account signals (WHO) with PIM product intelligence (WHY) to generate
a precisely targeted, personalized campaign that connects the right product to the right customer.

You will receive:
1. CRM data — company profile, industry, pain points, buying stage, ABM score
2. PXM product data — products enriched with WHY (scenario fit, vertical fit, bundle role, value tier)
3. Campaign scenario: onboarding | events | gifting
4. Tone: confident | urgent | premium | playful | exclusive

Output a single valid JSON object with these keys:
{
  "campaign_title": "max 8 words",
  "subject_line": "personalized, max 10 words",
  "hero_headline": "benefit-driven, max 12 words",
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
  "personalization_angle": "1-2 sentences on persona-specific angle",
  "campaign_notes": "strategic notes on timing, MOQ, vertical considerations",
  "email_html": "<full HTML email using brand colors #1A1A2E #D4AF37 #FFFFFF>",
  "landing_page_html": "<full HTML landing page matching email>"
}

Rules:
- Always reference the company name and industry in body_copy
- Match products to the account's pain_point and use_case
- email_html and landing_page_html must be complete, self-contained HTML documents
- Return ONLY valid JSON. No markdown, no explanation.
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