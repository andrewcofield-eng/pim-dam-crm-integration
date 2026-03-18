# Run this entire script in PowerShell from your backend directory
# cd C:\Users\andre\source\repos\pim-dam-crm-integration\backend

# ── ai_campaign_generator.py ──
@"
"""
ai_campaign_generator.py
Generates multi-channel campaign copy (email, ads, landing page)
using OpenAI GPT-4o, driven by the unified PIM + DAM + CRM payload.

Mirrors the pattern in abm_routes.py — uses OpenAI client directly,
reads OPENAI_API_KEY from environment (already set in Railway).
"""

import os
import json
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── Segment mock data (mirrors your existing ACCOUNTS pattern) ──
SEGMENTS = {
    "seg_001": {
        "segment_id":         "seg_001",
        "name":               "High-Value Repeat Buyers",
        "size":               2847,
        "avg_order_value":    284.50,
        "top_categories":     ["Electronics", "Premium Audio"],
        "purchase_frequency": "monthly",
        "churn_risk":         "low",
        "hubspot_list_id":    "hs_list_4421"
    },
    "seg_002": {
        "segment_id":         "seg_002",
        "name":               "At-Risk Subscribers",
        "size":               1203,
        "avg_order_value":    142.00,
        "top_categories":     ["Audio Accessories", "Budget Audio"],
        "purchase_frequency": "quarterly",
        "churn_risk":         "high",
        "hubspot_list_id":    "hs_list_4422"
    },
    "seg_003": {
        "segment_id":         "seg_003",
        "name":               "New Customer Acquisition",
        "size":               8921,
        "avg_order_value":    89.99,
        "top_categories":     ["Entry-Level Audio", "Cables"],
        "purchase_frequency": "one-time",
        "churn_risk":         "medium",
        "hubspot_list_id":    "hs_list_4423"
    }
}

# ── PIM product catalog mock (Cloudinary DAM assets referenced) ──
PRODUCTS = [
    {
        "sku":          "AUD-PRO-001",
        "name":         "ProSound Elite Headphones",
        "price":        299.99,
        "category":     "Premium Audio",
        "key_features": ["40hr battery", "ANC", "Hi-Res Audio"],
        "stock_status": "in_stock",
        "margin":       "high",
        "dam_hero_url": "https://res.cloudinary.com/demo/image/upload/headphones-hero.jpg"
    }
]

# ── Brand assets from DAM (Cloudinary) ──
BRAND_ASSETS = {
    "logo_url":            "https://res.cloudinary.com/demo/image/upload/logo-primary.svg",
    "color_palette":       ["#1A1A2E", "#16213E", "#0F3460", "#E94560"],
    "tone_of_voice":       "Premium, technical, aspirational",
    "brand_guidelines_url":"https://res.cloudinary.com/demo/image/upload/brand-v3.pdf"
}


def build_unified_payload(segment_id: str, override_goals: dict = None) -> dict:
    """Build the PIM + DAM + CRM unified payload for a given segment."""
    segment = SEGMENTS.get(segment_id, SEGMENTS["seg_001"])
    return {
        "customer_segment": segment,
        "products":         PRODUCTS,
        "brand_assets":     BRAND_ASSETS,
        "campaign_goals": {
            "objective":      "retention",
            "target_revenue": 50000,
            "timeline":       "30 days",
            "channels":       ["email", "paid_social", "landing_page"],
            **(override_goals or {})
        }
    }


def build_system_prompt(brief: dict) -> str:
    seg     = brief["customer_segment"]
    product = brief["products"][0]
    assets  = brief["brand_assets"]
    goals   = brief["campaign_goals"]

    return f"""You are an expert marketing copywriter for a premium brand.

BRAND VOICE: {assets["tone_of_voice"]}
COLOR PALETTE: {", ".join(assets["color_palette"])}

CUSTOMER SEGMENT:
- Name: {seg["name"]}
- Audience Size: {seg["size"]:,} customers
- Avg Order Value: ${seg["avg_order_value"]}
- Purchase Frequency: {seg["purchase_frequency"]}
- Top Categories: {", ".join(seg["top_categories"])}
- Churn Risk: {seg["churn_risk"]}

FEATURED PRODUCT (from PIM):
- Name: {product["name"]} (SKU: {product["sku"]})
- Price: ${product["price"]}
- Key Features: {", ".join(product["key_features"])}
- Stock Status: {product["stock_status"]}
- Margin Tier: {product["margin"]}

CAMPAIGN GOALS:
- Objective: {goals["objective"]}
- Target Revenue: ${goals["target_revenue"]:,}
- Timeline: {goals["timeline"]}
- Channels: {", ".join(goals["channels"])}

Generate copy that feels data-informed and segment-specific, not generic.
Reference the customer's purchase behaviour and the product's key differentiators.
Return ONLY valid JSON — no markdown, no extra text."""


USER_PROMPT = """Generate a full multi-channel campaign package. Return this exact JSON structure:

{
  "email": {
    "subject_lines": ["<option1>", "<option2>", "<option3>"],
    "preview_text": "<50-char preview>",
    "headline": "<main email headline>",
    "body_copy": "<2-3 paragraph email body>",
    "cta_button": "<CTA text>",
    "ps_line": "<P.S. urgency line>"
  },
  "ad_headlines": {
    "google_search": ["<headline1 max30chars>", "<headline2 max30chars>", "<headline3 max30chars>"],
    "meta_primary": "<primary ad text max125chars>",
    "meta_headline": "<ad headline max40chars>",
    "meta_description": "<description max30chars>"
  },
  "landing_page": {
    "hero_headline": "<bold hero headline>",
    "hero_subheadline": "<supporting subheadline>",
    "value_props": [
      { "icon": "<emoji>", "title": "<short title>", "description": "<1 sentence>" },
      { "icon": "<emoji>", "title": "<short title>", "description": "<1 sentence>" },
      { "icon": "<emoji>", "title": "<short title>", "description": "<1 sentence>" }
    ],
    "social_proof": "<testimonial or trust statement>",
    "cta_primary": "<primary CTA>",
    "cta_secondary": "<secondary CTA>"
  },
  "campaign_summary": {
    "strategy_rationale": "<2 sentences explaining the approach>",
    "key_message": "<single core message>",
    "urgency_hook": "<why act now>"
  }
}"""


def generate_campaign(segment_id: str, override_goals: dict = None) -> dict:
    """
    Main entry point. Builds the unified payload, calls GPT-4o,
    returns structured campaign copy + metadata.
    """
    start_ms = int(time.time() * 1000)

    brief = build_unified_payload(segment_id, override_goals)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": build_system_prompt(brief)},
            {"role": "user",   "content": USER_PROMPT}
        ],
        temperature=0.75,
        max_tokens=2000,
        response_format={"type": "json_object"}  # forces valid JSON — no parse errors
    )

    campaign_copy = json.loads(completion.choices[0].message.content)
    latency_ms    = int(time.time() * 1000) - start_ms

    return {
        "segment_id":    segment_id,
        "campaign_copy": campaign_copy,
        "model":         completion.model,
        "tokens_used":   completion.usage.total_tokens,
        "latency_ms":    latency_ms,
        "brief_snapshot": {
            "segment_name":  brief["customer_segment"]["name"],
            "product_sku":   brief["products"][0]["sku"],
            "objective":     brief["campaign_goals"]["objective"],
            "channels":      brief["campaign_goals"]["channels"]
        }
    }
"@
 | Set-Content -Encoding UTF8 "ai_campaign_generator.py"
Write-Host "✅ ai_campaign_generator.py written" -ForegroundColor Green

# ── campaign_routes.py ──
@"
"""
campaign_routes.py
FastAPI router for AI campaign generation + Shopify simulation.

Wire into main.py exactly like abm_routes.py:
    from campaign_routes import router as campaign_router
    app.include_router(campaign_router)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from ai_campaign_generator import generate_campaign
from shopify_simulator     import ShopifySimulator

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

# ── In-memory campaign store (same lightweight pattern as your ABM endpoints) ──
_campaign_store: List[dict] = []

# ── Singleton Shopify simulator ──
_shopify = ShopifySimulator()


# ── Request / Response models ──────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    segment_id:     str
    override_goals: Optional[dict] = None

class ShopifyStartRequest(BaseModel):
    interval_seconds: Optional[float] = 4.0
    max_orders:       Optional[int]   = None

class ManualOrderRequest(BaseModel):
    customer_type:  Optional[str] = None   # "new" | "returning" | "vip"
    product_sku:    Optional[str] = None   # e.g. "AUD-PRO-001"


# ── Campaign endpoints ─────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_campaign_endpoint(req: GenerateRequest):
    """
    Build unified PIM+DAM+CRM payload → send to GPT-4o → return campaign copy.
    Example:
        POST /campaigns/generate
        {"segment_id": "seg_001"}
    """
    valid_segments = ["seg_001", "seg_002", "seg_003"]
    if req.segment_id not in valid_segments:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid segment_id. Choose from: {valid_segments}"
        )

    try:
        result = generate_campaign(req.segment_id, req.override_goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    # Persist to in-memory store
    record = {
        "campaign_id":  str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result
    }
    _campaign_store.insert(0, record)   # newest first

    return record


@router.get("/")
async def list_campaigns(limit: int = 20, offset: int = 0):
    """Return all generated campaigns, newest first."""
    return {
        "total":     len(_campaign_store),
        "campaigns": _campaign_store[offset: offset + limit]
    }


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Retrieve a single campaign by ID."""
    for c in _campaign_store:
        if c["campaign_id"] == campaign_id:
            return c
    raise HTTPException(status_code=404, detail="Campaign not found")


# ── Shopify simulation endpoints ───────────────────────────────────────────────

@router.get("/shopify/status")
async def shopify_status():
    """Live metrics snapshot from the Shopify simulator."""
    return _shopify.get_status()


@router.post("/shopify/order")
async def shopify_manual_order(req: ManualOrderRequest):
    """
    Trigger a single simulated Shopify order.
    Example:
        POST /campaigns/shopify/order
        {"customer_type": "vip", "product_sku": "AUD-PRO-001"}
    """
    order = _shopify.generate_order(
        customer_type=req.customer_type,
        product_sku=req.product_sku
    )
    _shopify.record_order(order)
    return order


@router.post("/shopify/bulk")
async def shopify_bulk_orders(count: int = 10):
    """
    Generate N orders instantly (great for seeding the dashboard).
    Example: POST /campaigns/shopify/bulk?count=25
    """
    if count > 200:
        raise HTTPException(status_code=400, detail="Max 200 orders per bulk call")
    orders = []
    for _ in range(count):
        order = _shopify.generate_order()
        _shopify.record_order(order)
        orders.append(order)
    return {
        "generated": len(orders),
        "metrics":   _shopify.get_status()["metrics"]
    }


@router.get("/shopify/orders")
async def shopify_orders(limit: int = 20, offset: int = 0):
    """Paginated order log."""
    log = _shopify.order_log
    return {
        "total":  len(log),
        "orders": log[offset: offset + limit]
    }


@router.delete("/shopify/reset")
async def shopify_reset():
    """Reset the simulator metrics and order log (useful for demos)."""
    _shopify.reset()
    return {"message": "Simulator reset"}
"@
 | Set-Content -Encoding UTF8 "campaign_routes.py"
Write-Host "✅ campaign_routes.py written" -ForegroundColor Green

# ── shopify_simulator.py ──
@"
"""
shopify_simulator.py
Generates realistic Shopify order/transaction data for demo purposes.

Pure Python, no external dependencies — safe for Railway.
Mirrors the lightweight class pattern used in orchestrator.py.
"""

import random
import uuid
from datetime import datetime, timezone


PRODUCTS = [
    {"id": "PRD-001", "name": "ProSound Elite Headphones",  "price": 299.99, "sku": "AUD-PRO-001"},
    {"id": "PRD-002", "name": "Studio Monitor Speakers",    "price": 549.99, "sku": "AUD-STD-002"},
    {"id": "PRD-003", "name": "Portable DAC Amplifier",     "price": 149.99, "sku": "AUD-DAC-003"},
    {"id": "PRD-004", "name": "Premium Audio Cable Set",    "price":  49.99, "sku": "AUD-CAB-004"},
]

PRODUCT_BY_SKU = {p["sku"]: p for p in PRODUCTS}

FIRST_NAMES = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Drew"]
LAST_NAMES  = ["Chen", "Smith", "Patel", "Johnson", "Garcia", "Kim", "Brown", "Osei"]
CUSTOMER_TYPES = ["new", "returning", "vip"]


class ShopifySimulator:
    """
    Stateful simulator for Shopify orders and transactions.
    Accumulates metrics in-memory — persisted for the lifetime of the process.
    """

    def __init__(self):
        self._order_counter = 10000
        self.order_log: list  = []          # capped at 500 most recent
        self.metrics: dict    = {
            "total_orders":          0,
            "total_revenue":         0.0,
            "new_customers":         0,
            "returning_customers":   0,
            "vip_customers":         0,
            "refunds":               0,
            "refund_amount":         0.0,
            "top_products":          {},
            "last_order_at":         None
        }

    # ── Order generation ───────────────────────────────────────────────────────

    def generate_order(
        self,
        customer_type: str = None,
        product_sku:   str = None
    ) -> dict:
        """Generate one realistic Shopify order dict."""
        self._order_counter += 1

        # Pick product
        if product_sku and product_sku in PRODUCT_BY_SKU:
            product = PRODUCT_BY_SKU[product_sku]
        else:
            product = random.choice(PRODUCTS)

        # Pick customer type
        ctype = customer_type if customer_type in CUSTOMER_TYPES else random.choice(CUSTOMER_TYPES)

        qty          = random.randint(1, 3)
        subtotal     = round(product["price"] * qty, 2)
        tax          = round(subtotal * 0.08, 2)
        total        = round(subtotal + tax, 2)
        order_id     = f"ORD-{self._order_counter}"
        customer_num = random.randint(1000, 9999)

        return {
            "id":               order_id,
            "shopify_order_id": f"gid://shopify/Order/{self._order_counter}",
            "created_at":       datetime.now(timezone.utc).isoformat(),
            "financial_status":   "paid",
            "fulfillment_status": "unfulfilled",
            "customer": {
                "id":           f"CUST-{customer_num}",
                "email":        f"customer{self._order_counter}@example.com",
                "first_name":   random.choice(FIRST_NAMES),
                "last_name":    random.choice(LAST_NAMES),
                "type":         ctype,
                "orders_count": (
                    random.randint(5, 25) if ctype == "vip"
                    else random.randint(2, 5) if ctype == "returning"
                    else 1
                ),
                "total_spent": str(
                    round(random.uniform(500, 2500), 2) if ctype == "vip"
                    else round(random.uniform(50, 450), 2)
                )
            },
            "line_items": [{
                "product_id":  product["id"],
                "sku":         product["sku"],
                "title":       product["name"],
                "quantity":    qty,
                "price":       str(product["price"]),
                "total_price": str(subtotal)
            }],
            "subtotal_price": str(subtotal),
            "total_tax":      str(tax),
            "total_price":    str(total),
            "currency":       "USD",
            "tags":           [ctype, product["sku"].split("-")[1].lower()]
        }

    def generate_refund(self, order: dict) -> dict:
        """Generate a refund event linked to an existing order."""
        reasons = ["customer_request", "defective", "not_as_described", "other"]
        return {
            "id":              f"REF-{uuid.uuid4().hex[:8].upper()}",
            "order_id":        order["id"],
            "created_at":      datetime.now(timezone.utc).isoformat(),
            "refund_line_items": order["line_items"],
            "total_refunded":  order["total_price"],
            "reason":          random.choice(reasons)
        }

    # ── Metrics accumulation ───────────────────────────────────────────────────

    def record_order(self, order: dict) -> None:
        """Append order to log and update live metrics."""
        # Cap log at 500
        self.order_log.insert(0, order)
        if len(self.order_log) > 500:
            self.order_log.pop()

        # Metrics
        ctype = order["customer"]["type"]
        self.metrics["total_orders"]   += 1
        self.metrics["total_revenue"]  += float(order["total_price"])
        self.metrics["last_order_at"]   = order["created_at"]

        if ctype == "new":
            self.metrics["new_customers"]       += 1
        elif ctype == "returning":
            self.metrics["returning_customers"] += 1
        elif ctype == "vip":
            self.metrics["vip_customers"]       += 1

        sku = order["line_items"][0]["sku"]
        self.metrics["top_products"][sku] = self.metrics["top_products"].get(sku, 0) + 1

    def record_refund(self, refund: dict) -> None:
        """Update metrics when a refund occurs."""
        self.metrics["refunds"]       += 1
        self.metrics["refund_amount"] += float(refund["total_refunded"])

    # ── Status snapshot ────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Return a clean metrics snapshot for the API response."""
        top_products = sorted(
            self.metrics["top_products"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_orders_logged": len(self.order_log),
            "metrics": {
                **self.metrics,
                "total_revenue":  round(self.metrics["total_revenue"], 2),
                "refund_amount":  round(self.metrics["refund_amount"], 2),
                "net_revenue":    round(
                    self.metrics["total_revenue"] - self.metrics["refund_amount"], 2
                ),
                "top_products":   [
                    {"sku": sku, "order_count": count}
                    for sku, count in top_products
                ]
            }
        }

    def reset(self) -> None:
        """Wipe all state — useful for demo resets."""
        self.__init__()
"@
 | Set-Content -Encoding UTF8 "shopify_simulator.py"
Write-Host "✅ shopify_simulator.py written" -ForegroundColor Green

Write-Host ""
Write-Host "All 3 files written. Now patching main.py..." -ForegroundColor Cyan

# ── Patch main.py: add campaign_router (only if not already present) ──
$mainContent = Get-Content main.py -Raw
if ($mainContent -notmatch "campaign_routes") {
    Add-Content -Encoding UTF8 main.py ""
    Add-Content -Encoding UTF8 main.py "from campaign_routes import router as campaign_router"
    Add-Content -Encoding UTF8 main.py "app.include_router(campaign_router)"
    Write-Host "✅ main.py patched with campaign_router" -ForegroundColor Green
} else {
    Write-Host "ℹ️  main.py already has campaign_router - skipping" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Done! Run: python main.py  to test locally" -ForegroundColor Green