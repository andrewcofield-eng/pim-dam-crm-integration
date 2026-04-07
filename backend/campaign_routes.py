from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import json
import os
import httpx

# ─── Prompts ──────────────────────────────────────────────────────────────────

ONBOARDING_CAMPAIGN_PROMPT = """
You are an expert B2B promotional products campaign strategist for AgenticFlow Marketing.

Your job is to generate a complete, personalized onboarding campaign brief for a specific company account.

You will receive:
- Account data from HubSpot CRM (company name, industry, size, buyer persona)
- A list of enriched products filtered for onboarding suitability
- A campaign scenario: Employee Onboarding / New Hire Kit

Your output must be a structured JSON campaign brief with the following sections:

1. campaign_title: A short, punchy campaign name (max 8 words)
2. subject_line: Email subject line (max 10 words, personalized to company name)
3. hero_headline: Hero section headline (max 12 words, benefit-driven)
4. body_copy: 2-3 sentences of persuasive campaign body copy. Reference the company name and industry. Focus on the value of making new hires feel welcome and connected to the brand.
5. product_recommendations: Array of 2-4 recommended products. For each product include:
   - sku
   - name
   - reason: Why this product fits this account's onboarding scenario (1 sentence)
   - personalization_note: How to personalize it (logo, name, etc.)
6. bundle_suggestion: A suggested bundle name and the SKUs it includes (pick the anchor + 1-2 supporting items)
7. cta_text: Call-to-action button text (max 6 words)
8. personalization_angle: 1-2 sentences on how to personalize this campaign for the specific buyer persona
9. campaign_notes: Any strategic notes about timing, MOQ, or vertical-specific considerations

Rules:
- Only recommend products where onboarding_fit is "High" or "Medium"
- Prefer products where bundle_role is "Anchor" for the primary recommendation
- If the account is in SaaS or tech, lead with premium feel and brand identity
- If the account is in Professional Services, emphasize quality and client impression
- Keep all copy professional, warm, and human — never generic
- Always return valid JSON only. No markdown, no explanation outside the JSON.
"""

EVENTS_CAMPAIGN_PROMPT = """
You are an expert B2B promotional products campaign strategist for AgenticFlow Marketing.

Your job is to generate a complete, personalized event/trade show campaign brief for a specific company account.

You will receive:
- Account data from HubSpot CRM (company name, industry, size, buyer persona)
- A list of enriched products filtered for event suitability
- A campaign scenario: Event / Trade Show / Conference

Your output must be a structured JSON campaign brief with the following sections:

1. campaign_title: A short, punchy campaign name (max 8 words)
2. subject_line: Email subject line (max 10 words, personalized to company name)
3. hero_headline: Hero section headline (max 12 words, high energy and action-oriented)
4. body_copy: 2-3 sentences of persuasive campaign body copy. Reference the company name. Focus on standing out on the trade show floor, driving booth traffic, and creating memorable brand impressions.
5. product_recommendations: Array of 2-4 recommended products. For each product include:
   - sku
   - name
   - reason: Why this product fits this account's event scenario (1 sentence)
   - personalization_note: How to personalize it for the event (logo, event name, booth theme, etc.)
6. bundle_suggestion: A suggested event kit bundle name and the SKUs it includes
7. cta_text: Call-to-action button text (max 6 words)
8. personalization_angle: 1-2 sentences on how to personalize this campaign for the specific buyer persona
9. campaign_notes: Strategic notes about lead time, event timing, quantity planning, and giveaway strategy

Rules:
- Only recommend products where event_fit is "High" or "Medium"
- Prefer high-visibility, portable, and giveaway-friendly products
- Prefer products where bundle_role is "Anchor" or "Supporting" for event kits
- If the account is in SaaS or tech, emphasize sleek, modern brand presence
- If the account is in Hospitality or Events, emphasize experiential and premium feel
- Keep copy energetic, confident, and action-oriented — never generic
- Always return valid JSON only. No markdown, no explanation outside the JSON.
"""

GIFTING_CAMPAIGN_PROMPT = """
You are an expert B2B promotional products campaign strategist for AgenticFlow Marketing.

Your job is to generate a complete, personalized executive gifting campaign brief for a specific company account.

You will receive:
- Account data from HubSpot CRM (company name, industry, size, buyer persona, gifting occasion)
- A list of enriched products filtered for gifting suitability
- A campaign scenario: Executive Gifting / Client Appreciation

Your output must be a structured JSON campaign brief with the following sections:

1. campaign_title: A short, sophisticated campaign name (max 8 words)
2. subject_line: Email subject line (max 10 words, elegant and personalized)
3. hero_headline: Hero section headline (max 12 words, relationship-focused and premium)
4. body_copy: 2-3 sentences of persuasive campaign body copy. Reference the company name and industry. Focus on strengthening relationships, expressing genuine appreciation, and the lasting impression a premium gift creates.
5. product_recommendations: Array of 2-4 recommended products. For each product include:
   - sku
   - name
   - reason: Why this product fits this account's executive gifting scenario (1 sentence)
   - personalization_note: How to personalize it for the recipient (monogram, logo, gift wrapping, etc.)
6. bundle_suggestion: A suggested premium gift set name and the SKUs it includes
7. cta_text: Call-to-action button text (max 6 words, sophisticated tone)
8. personalization_angle: 1-2 sentences on how to personalize this campaign for the specific buyer persona and recipient tier
9. campaign_notes: Strategic notes about presentation, packaging, delivery timing, and relationship context

Rules:
- Only recommend products where gifting_fit is "High" or "Medium"
- Strongly prefer products where value_tier is "premium", "luxury", or "mid_range"
- Prefer products where bundle_role is "Anchor" or "Standalone"
- If the account is in Financial Services or Real Estate, emphasize exclusivity and lasting value
- If the account is in Hospitality, emphasize experiential quality and sensory appeal
- If the account is in SaaS or Professional Services, emphasize thoughtfulness and brand alignment
- Keep all copy sophisticated, warm, and relationship-driven — never transactional or generic
- Always return valid JSON only. No markdown, no explanation outside the JSON.
"""

# ─── Analytics ────────────────────────────────────────────────────────────────

ANALYTICS_FILE = os.path.join(os.path.dirname(__file__), "campaign_analytics.json")

def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"views": [], "generations": 0, "exports": 0}
    return {"views": [], "generations": 0, "exports": 0}

def save_analytics(data):
    try:
        with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"Failed to save analytics: {e}")

_analytics = load_analytics()

# ─── Campaign Store ───────────────────────────────────────────────────────────

CAMPAIGNS_FILE = os.path.join(os.path.dirname(__file__), "campaigns_data.json")

def load_campaigns():
    if os.path.exists(CAMPAIGNS_FILE):
        try:
            with open(CAMPAIGNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_campaigns(campaigns):
    try:
        with open(CAMPAIGNS_FILE, "w", encoding="utf-8") as f:
            json.dump(campaigns, f, indent=2, default=str)
    except Exception as e:
        print(f"Failed to save campaigns: {e}")

_campaign_store: List[dict] = load_campaigns()

# ─── Imports ──────────────────────────────────────────────────────────────────

from ai_campaign_generator import generate_campaign
from shopify_simulator import ShopifySimulator

router   = APIRouter(prefix="/ai-campaigns", tags=["Campaigns"])
_shopify = ShopifySimulator()

# Auto-seed Shopify simulator with 40 orders on startup
import threading

def _seed_shopify():
    import time
    time.sleep(3)
    try:
        for _ in range(40):
            o = _shopify.generate_order()
            _shopify.record_order(o)
        print(f"✅ Shopify simulator seeded with 40 orders")
    except Exception as e:
        print(f"⚠️ Shopify seed failed: {e}")

threading.Thread(target=_seed_shopify, daemon=True).start()

# ─── Models ───────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    segment_id:     str
    override_goals: Optional[dict] = None

class ManualOrderRequest(BaseModel):
    customer_type: Optional[str] = None
    product_sku:   Optional[str] = None

# ─── Helpers ──────────────────────────────────────────────────────────────────

def format_products_for_prompt(products: list) -> str:
    """Format enriched products into a clean text block for the AI prompt."""
    lines = []
    for p in products:
        scores = p.get("scenario_scores", {})
        merch  = p.get("merchandising", {})
        fit    = p.get("marketing_fit", {})
        msg    = p.get("messaging", {})

        lines.append(f"""
SKU: {p.get('sku')} | Name: {p.get('name')} | Price: ${p.get('price')}
  Category: {p.get('category')}
  Onboarding Fit: {scores.get('onboarding')} | Event Fit: {scores.get('events')} | Gifting Fit: {scores.get('gifting')}
  Ideal Audience: {', '.join(fit.get('ideal_audience', []))}
  Vertical Fit: {', '.join(fit.get('vertical_fit', []))}
  Bundle Role: {merch.get('bundle_role')} | Value Tier: {merch.get('value_tier')}
  Personalization Suitability: {merch.get('personalization_suitability')}
  Complementary SKUs: {', '.join(merch.get('complementary_skus', []))}
  Recommended CTA: {msg.get('recommended_cta')}
""")
    return "\n".join(lines)


def flatten_campaign_copy(campaign_copy: dict) -> dict:
    """
    GPT-4o returns nested objects for email, ad_headlines, landing_page.
    This flattens them into the top-level keys the frontend JS expects.
    """
    email_block   = campaign_copy.get("email", {})
    ad_block      = campaign_copy.get("ad_headlines", {})
    landing_block = campaign_copy.get("landing_page", {})
    summary_block = campaign_copy.get("campaign_summary", {})

    if isinstance(email_block, dict):
        subject = email_block.get("subject_lines", [""])[0]
        email_copy = "\n\n".join(filter(None, [
            f"Subject: {subject}" if subject else "",
            email_block.get("headline", ""),
            email_block.get("body_copy", ""),
            f"CTA: {email_block.get('cta_button', '')}",
            f"PS: {email_block.get('ps_line', '')}"
        ])).strip()
    else:
        email_copy = str(email_block)

    if isinstance(ad_block, dict):
        ad_headlines = (
            ad_block.get("google_search", []) +
            [ad_block.get("meta_headline", "")] +
            [ad_block.get("meta_primary", "")]
        )
        ad_headlines = [h for h in ad_headlines if h]
    elif isinstance(ad_block, list):
        ad_headlines = ad_block
    else:
        ad_headlines = [str(ad_block)] if ad_block else []

    if isinstance(landing_block, dict):
        props = landing_block.get("value_props", [])
        props_text = " | ".join(
            f"{p.get('title','')}: {p.get('description','')}"
            for p in props if isinstance(p, dict)
        )
        landing_page_copy = "\n\n".join(filter(None, [
            landing_block.get("hero_headline", ""),
            landing_block.get("hero_subheadline", ""),
            props_text,
            landing_block.get("social_proof", ""),
            f"CTA: {landing_block.get('cta_primary', '')}"
        ])).strip()
    else:
        landing_page_copy = str(landing_block)

    if isinstance(summary_block, dict):
        campaign_summary = " | ".join(filter(None, [
            summary_block.get("strategy_rationale", ""),
            summary_block.get("key_message", ""),
            summary_block.get("urgency_hook", "")
        ])).strip()
    else:
        campaign_summary = str(summary_block)

    return {
        "email_copy":        email_copy,
        "ad_headlines":      ad_headlines,
        "landing_page_copy": landing_page_copy,
        "campaign_summary":  campaign_summary
    }

def select_scenario_from_crm(account: dict) -> str:
    """
    Auto-select campaign scenario based on CRM account signals.
    Priority order: explicit hint → industry → persona → default
    """
    # 1. Explicit hint from CRM (highest priority)
    hint = (account.get("campaign_hint") or "").lower()
    if hint in ["onboarding", "events", "gifting"]:
        return hint

    industry = (account.get("industry") or "").lower()
    persona  = (account.get("buyer_persona") or "").lower()
    occasion = (account.get("gifting_occasion") or "").lower()
    event    = (account.get("event_name") or "").lower()

    # 2. Event signals
    if event or any(k in industry for k in ["events", "hospitality", "conference"]):
        return "events"
    if any(k in persona for k in ["events", "marketing", "sales_enablement"]):
        return "events"

    # 3. Gifting signals
    if occasion or any(k in industry for k in ["financial", "real_estate", "luxury"]):
        return "gifting"
    if any(k in persona for k in ["executive", "leadership", "c_suite"]):
        return "gifting"

    # 4. Onboarding signals
    if any(k in persona for k in ["people_ops", "hr", "human_resources", "procurement"]):
        return "onboarding"
    if any(k in industry for k in ["saas", "tech", "software", "professional_services"]):
        return "onboarding"

    # 5. Default
    return "onboarding"


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/onboarding")
async def generate_onboarding_campaign(request: dict):
    """
    Generate an AI-powered onboarding campaign brief.
    POST /ai-campaigns/onboarding
    """
    try:
        account      = request.get("account", {})
        company_name = account.get("company_name", "Your Company")
        industry     = account.get("industry", "general_b2b")
        persona      = account.get("buyer_persona", "people_ops_hr")
        contact_name = account.get("contact_name", "")
        company_size = account.get("company_size", "unknown")

        # Step 1: Fetch onboarding-ready products
        async with httpx.AsyncClient() as client:
            products_response = await client.get(
                "http://localhost:8000/products/export?scenario=onboarding",
                timeout=10.0
            )
            products = products_response.json().get("products", [])

        if not products:
            raise HTTPException(status_code=404, detail="No onboarding-ready products found")

        # Step 2: Build user message
        user_message = f"""
Generate an onboarding campaign brief for the following account:

ACCOUNT:
- Company: {company_name}
- Industry: {industry}
- Company Size: {company_size}
- Buyer Persona: {persona}
- Contact Name: {contact_name}

AVAILABLE ONBOARDING PRODUCTS:
{format_products_for_prompt(products)}

Generate the campaign brief now. Return valid JSON only.
"""

        # Step 3: Call OpenAI
        from openai import OpenAI
        client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": ONBOARDING_CAMPAIGN_PROMPT},
                {"role": "user",   "content": user_message}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Step 4: Parse and return
        campaign_brief = json.loads(response.choices[0].message.content)

        return {
            "status": "success",
            "scenario": "onboarding",
            "account": {
                "company_name": company_name,
                "industry":     industry,
                "persona":      persona
            },
            "products_evaluated": len(products),
            "campaign_brief":     campaign_brief
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events")
async def generate_events_campaign(request: dict):
    """
    Generate an AI-powered event/trade show campaign brief.
    POST /ai-campaigns/events
    """
    try:
        account      = request.get("account", {})
        company_name = account.get("company_name", "Your Company")
        industry     = account.get("industry", "general_b2b")
        persona      = account.get("buyer_persona", "marketing")
        contact_name = account.get("contact_name", "")
        company_size = account.get("company_size", "unknown")
        event_name   = account.get("event_name", "upcoming event")
        event_date   = account.get("event_date", "")

        # Step 1: Fetch event-ready products
        async with httpx.AsyncClient() as client:
            products_response = await client.get(
                "http://localhost:8000/products/export?scenario=events",
                timeout=10.0
            )
            products = products_response.json().get("products", [])

        if not products:
            raise HTTPException(status_code=404, detail="No event-ready products found")

        # Step 2: Build user message
        user_message = f"""
Generate an event/trade show campaign brief for the following account:

ACCOUNT:
- Company: {company_name}
- Industry: {industry}
- Company Size: {company_size}
- Buyer Persona: {persona}
- Contact Name: {contact_name}
- Event Name: {event_name}
- Event Date: {event_date if event_date else "TBD"}

AVAILABLE EVENT PRODUCTS:
{format_products_for_prompt(products)}

Generate the campaign brief now. Return valid JSON only.
"""

        # Step 3: Call OpenAI
        from openai import OpenAI
        client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EVENTS_CAMPAIGN_PROMPT},
                {"role": "user",   "content": user_message}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Step 4: Parse and return
        campaign_brief = json.loads(response.choices[0].message.content)

        return {
            "status": "success",
            "scenario": "events",
            "account": {
                "company_name": company_name,
                "industry":     industry,
                "persona":      persona,
                "event_name":   event_name
            },
            "products_evaluated": len(products),
            "campaign_brief":     campaign_brief
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gifting")
async def generate_gifting_campaign(request: dict):
    """
    Generate an AI-powered executive gifting campaign brief.
    POST /ai-campaigns/gifting
    """
    try:
        account          = request.get("account", {})
        company_name     = account.get("company_name", "Your Company")
        industry         = account.get("industry", "general_b2b")
        persona          = account.get("buyer_persona", "executive_leadership")
        contact_name     = account.get("contact_name", "")
        company_size     = account.get("company_size", "unknown")
        recipient_tier   = account.get("recipient_tier", "executive")
        gifting_occasion = account.get("gifting_occasion", "client appreciation")
        budget_per_unit  = account.get("budget_per_unit", "")

        # Step 1: Fetch gifting-ready products
        async with httpx.AsyncClient() as client:
            products_response = await client.get(
                "http://localhost:8000/products/export?scenario=gifting",
                timeout=10.0
            )
            products = products_response.json().get("products", [])

        if not products:
            raise HTTPException(status_code=404, detail="No gifting-ready products found")

        # Step 2: Build user message
        user_message = f"""
Generate an executive gifting campaign brief for the following account:

ACCOUNT:
- Company: {company_name}
- Industry: {industry}
- Company Size: {company_size}
- Buyer Persona: {persona}
- Contact Name: {contact_name}
- Recipient Tier: {recipient_tier}
- Gifting Occasion: {gifting_occasion}
- Budget Per Unit: {"$" + str(budget_per_unit) if budget_per_unit else "flexible"}

AVAILABLE GIFTING PRODUCTS:
{format_products_for_prompt(products)}

Generate the campaign brief now. Return valid JSON only.
"""

        # Step 3: Call OpenAI
        from openai import OpenAI
        client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GIFTING_CAMPAIGN_PROMPT},
                {"role": "user",   "content": user_message}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Step 4: Parse and return
        campaign_brief = json.loads(response.choices[0].message.content)

        return {
            "status": "success",
            "scenario": "gifting",
            "account": {
                "company_name":     company_name,
                "industry":         industry,
                "persona":          persona,
                "recipient_tier":   recipient_tier,
                "gifting_occasion": gifting_occasion
            },
            "products_evaluated": len(products),
            "campaign_brief":     campaign_brief
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/smart-generate")
async def smart_generate_campaign(request: dict):
    """
    Unified campaign generator — auto-selects scenario from CRM signals.
    POST /ai-campaigns/smart-generate

    Expects:
    {
        "account": {
            "company_name": "Acme Corp",
            "industry": "financial_services",
            "buyer_persona": "executive_leadership",
            "contact_name": "James Whitfield",
            "company_size": "201-500",

            // Optional overrides:
            "campaign_hint": "gifting",       // force a scenario
            "event_name": "SaaStr 2026",      // triggers events
            "gifting_occasion": "Q4 gifts",   // triggers gifting
            "budget_per_unit": "150",
            "recipient_tier": "executive"
        }
    }
    """
    try:
        account  = request.get("account", {})

        # ── Step 1: Auto-select scenario ──────────────────
        scenario = select_scenario_from_crm(account)
        print(f"[smart-generate] Selected scenario: {scenario} for {account.get('company_name')}")

        # ── Step 2: Fetch matching products ───────────────
        async with httpx.AsyncClient() as client:
            products_response = await client.get(
                f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/products/export?scenario={scenario}",
                timeout=10.0
            )
            products = products_response.json().get("products", [])

        if not products:
            raise HTTPException(
                status_code=404,
                detail=f"No {scenario}-ready products found"
            )

        # ── Step 3: Select correct system prompt ──────────
        prompt_map = {
            "onboarding": ONBOARDING_CAMPAIGN_PROMPT,
            "events":     EVENTS_CAMPAIGN_PROMPT,
            "gifting":    GIFTING_CAMPAIGN_PROMPT,
        }
        system_prompt = prompt_map[scenario]

        # ── Step 4: Build user message ────────────────────
        company_name  = account.get("company_name", "Your Company")
        industry      = account.get("industry", "general_b2b")
        persona       = account.get("buyer_persona", "marketing")
        contact_name  = account.get("contact_name", "")
        company_size  = account.get("company_size", "unknown")
        event_name    = account.get("event_name", "")
        occasion      = account.get("gifting_occasion", "")
        budget        = account.get("budget_per_unit", "")
        recipient     = account.get("recipient_tier", "")

        # Scenario-specific context lines
        extra = ""
        if scenario == "events" and event_name:
            extra = f"- Event Name: {event_name}\n"
        elif scenario == "gifting":
            if occasion: extra += f"- Gifting Occasion: {occasion}\n"
            if budget:   extra += f"- Budget Per Unit: ${budget}\n"
            if recipient:extra += f"- Recipient Tier: {recipient}\n"

        user_message = f"""
Generate a {scenario} campaign brief for the following account:

ACCOUNT:
- Company: {company_name}
- Industry: {industry}
- Company Size: {company_size}
- Buyer Persona: {persona}
- Contact Name: {contact_name}
{extra}
AVAILABLE {scenario.upper()} PRODUCTS:
{format_products_for_prompt(products)}

Generate the campaign brief now. Return valid JSON only.
"""

        # ── Step 5: Call OpenAI ───────────────────────────
        from openai import OpenAI
        client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        campaign_brief = json.loads(response.choices[0].message.content)

        # ── Step 6: Return ────────────────────────────────
        return {
            "status":             "success",
            "scenario_selected":  scenario,
            "scenario_reasoning": f"Auto-selected based on industry='{industry}', persona='{persona}'",
            "account": {
                "company_name": company_name,
                "industry":     industry,
                "persona":      persona,
            },
            "products_evaluated": len(products),
            "campaign_brief":     campaign_brief
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_campaign_endpoint(req: GenerateRequest):
    valid = ["seg_001", "seg_002", "seg_003"]
    if req.segment_id not in valid:
        raise HTTPException(status_code=400, detail=f"segment_id must be one of {valid}")
    try:
        result = generate_campaign(req.segment_id, req.override_goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    flat = flatten_campaign_copy(result.get("campaign_copy", {}))

    record = {
        "campaign_id":  str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result,
        **flat
    }

    _campaign_store.insert(0, record)
    save_campaigns(_campaign_store)

    return record


@router.get("/history")
async def get_campaign_history(limit: int = 50):
    return {"total": len(_campaign_store), "campaigns": _campaign_store[:limit]}


@router.get("/analytics/summary")
async def get_campaign_analytics():
    total_views = len([v for v in _analytics["views"] if v.get("type") == "view"])
    total_used  = len([v for v in _analytics["views"] if v.get("type") == "use"])

    campaign_stats = {}
    for view in _analytics["views"]:
        cid = view.get("campaign_id")
        if cid not in campaign_stats:
            campaign_stats[cid] = {"views": 0, "used": 0}
        if view.get("type") == "view":
            campaign_stats[cid]["views"] += 1
        elif view.get("type") == "use":
            campaign_stats[cid]["used"] += 1

    return {
        "total_campaigns_generated": len(_campaign_store),
        "total_views":    total_views,
        "total_used":     total_used,
        "conversion_rate": round(total_used / total_views * 100, 1) if total_views > 0 else 0,
        "per_campaign_stats": campaign_stats,
        "recent_activity": _analytics["views"][-10:]
    }


@router.get("/shopify/status")
async def shopify_status():
    return _shopify.get_status()


@router.post("/shopify/order")
async def shopify_manual_order(req: ManualOrderRequest):
    order = _shopify.generate_order(customer_type=req.customer_type, product_sku=req.product_sku)
    _shopify.record_order(order)
    return order


@router.post("/shopify/bulk")
async def shopify_bulk(count: int = 10):
    if count > 200:
        raise HTTPException(status_code=400, detail="Max 200 per bulk call")
    orders = []
    for _ in range(count):
        o = _shopify.generate_order()
        _shopify.record_order(o)
        orders.append(o)
    return {"generated": len(orders), "metrics": _shopify.get_status()["metrics"]}


@router.get("/shopify/orders")
async def shopify_orders(limit: int = 20, offset: int = 0):
    log = _shopify.order_log
    return {"total": len(log), "orders": log[offset: offset + limit]}


@router.delete("/shopify/reset")
async def shopify_reset():
    _shopify.reset()
    return {"message": "Simulator reset"}


@router.get("/")
async def list_campaigns(limit: int = 20, offset: int = 0):
    return {"total": len(_campaign_store), "campaigns": _campaign_store[offset: offset + limit]}


@router.post("/{campaign_id}/view")
async def track_campaign_view(campaign_id: str):
    _analytics["views"].append({
        "campaign_id": campaign_id,
        "viewed_at":   datetime.now(timezone.utc).isoformat(),
        "type":        "view"
    })
    _analytics["generations"] = len(_campaign_store)
    save_analytics(_analytics)
    return {"status": "tracked", "campaign_id": campaign_id}
@router.post("/{campaign_id}/use")
async def track_campaign_use(campaign_id: str):
    _analytics["views"].append({
        "campaign_id": campaign_id,
        "used_at":     datetime.now(timezone.utc).isoformat(),
        "type":        "use"
    })
    _analytics["exports"] += 1
    save_analytics(_analytics)
    return {"status": "marked_used", "campaign_id": campaign_id}


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    for c in _campaign_store:
        if c["campaign_id"] == campaign_id:
            return c
    raise HTTPException(status_code=404, detail="Campaign not found")