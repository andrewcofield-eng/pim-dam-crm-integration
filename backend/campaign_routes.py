from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

import json
import os

# Persist campaigns to JSON file
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

# Initialize store from disk
_campaign_store: List[dict] = load_campaigns()

from ai_campaign_generator import generate_campaign
from shopify_simulator import ShopifySimulator

router   = APIRouter(prefix="/ai-campaigns", tags=["Campaigns"])
_shopify = ShopifySimulator()

class GenerateRequest(BaseModel):
    segment_id:     str
    override_goals: Optional[dict] = None

class ManualOrderRequest(BaseModel):
    customer_type: Optional[str] = None
    product_sku:   Optional[str] = None


def flatten_campaign_copy(campaign_copy: dict) -> dict:
    """
    GPT-4o returns nested objects for email, ad_headlines, landing_page.
    This flattens them into the top-level keys the frontend JS expects:
      email_copy, ad_headlines (list), landing_page_copy, campaign_summary
    """
    email_block   = campaign_copy.get("email", {})
    ad_block      = campaign_copy.get("ad_headlines", {})
    landing_block = campaign_copy.get("landing_page", {})
    summary_block = campaign_copy.get("campaign_summary", {})

    # --- email_copy: flat string ---
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

    # --- ad_headlines: flat list of strings ---
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

    # --- landing_page_copy: flat string ---
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

    # --- campaign_summary: flat string ---
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


@router.post("/generate")
async def generate_campaign_endpoint(req: GenerateRequest):
    valid = ["seg_001", "seg_002", "seg_003"]
    if req.segment_id not in valid:
        raise HTTPException(status_code=400, detail=f"segment_id must be one of {valid}")
    try:
        result = generate_campaign(req.segment_id, req.override_goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    # Flatten nested GPT-4o response into top-level keys for the frontend
    flat = flatten_campaign_copy(result.get("campaign_copy", {}))

    record = {
        "campaign_id":  str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result,   # includes campaign_copy (nested), model, tokens_used, latency_ms, brief_snapshot
        **flat      # adds/overwrites with email_copy, ad_headlines, landing_page_copy, campaign_summary
    }
    
    # Persist to disk
    _campaign_store.insert(0, record)
    save_campaigns(_campaign_store)
    
    return record

@router.get("/history")
async def get_campaign_history(limit: int = 50):
    """Return list of previously generated campaigns."""
    return {
        "total": len(_campaign_store),
        "campaigns": _campaign_store[:limit]
    }

@router.get("/")
async def list_campaigns(limit: int = 20, offset: int = 0):
    return {"total": len(_campaign_store), "campaigns": _campaign_store[offset: offset + limit]}


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


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    for c in _campaign_store:
        if c["campaign_id"] == campaign_id:
            return c
    raise HTTPException(status_code=404, detail="Campaign not found")