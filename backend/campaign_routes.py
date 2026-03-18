from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from ai_campaign_generator import generate_campaign
from shopify_simulator import ShopifySimulator

router   = APIRouter(prefix="/ai-campaigns", tags=["Campaigns"])
_store:  List[dict] = []
_shopify = ShopifySimulator()


class GenerateRequest(BaseModel):
    segment_id:     str
    override_goals: Optional[dict] = None

class ManualOrderRequest(BaseModel):
    customer_type: Optional[str] = None
    product_sku:   Optional[str] = None


@router.post("/generate")
async def generate_campaign_endpoint(req: GenerateRequest):
    valid = ["seg_001", "seg_002", "seg_003"]
    if req.segment_id not in valid:
        raise HTTPException(status_code=400, detail=f"segment_id must be one of {valid}")
    try:
        result = generate_campaign(req.segment_id, req.override_goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
    record = {"campaign_id": str(uuid.uuid4()), "generated_at": datetime.now(timezone.utc).isoformat(), **result}
    _store.insert(0, record)
    return record


@router.get("/")
async def list_campaigns(limit: int = 20, offset: int = 0):
    return {"total": len(_store), "campaigns": _store[offset: offset + limit]}


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
    for c in _store:
        if c["campaign_id"] == campaign_id:
            return c
    raise HTTPException(status_code=404, detail="Campaign not found")

