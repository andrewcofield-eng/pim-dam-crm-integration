"""
hubspot_routes.py  —  HubSpot writeback endpoints
Wired into main.py as:  app.include_router(hubspot_router)
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
import httpx

router = APIRouter(prefix="/hubspot", tags=["HubSpot"])

HUBSPOT_API_BASE = "https://api.hubapi.com"


def get_hubspot_token() -> str:
    token = os.getenv("HUBSPOT_ACCESS_TOKEN") or os.getenv("HUBSPOT_API_KEY")
    if not token:
        raise ValueError("HUBSPOT_ACCESS_TOKEN environment variable not set")
    return token


class NoteRequest(BaseModel):
    contact_id: str
    note:       str


@router.post("/note")
async def write_engagement_note(req: NoteRequest):
    """
    Writes a campaign as an engagement note on the matching HubSpot contact.
    Uses the HubSpot Engagements API v1 (works on free tier).
    """
    # Guard: reject obviously bad contact_ids before hitting HubSpot
    if not req.contact_id or req.contact_id in ("None", "null", "", "undefined"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid contact_id: '{req.contact_id}'"
        )

    try:
        token = get_hubspot_token()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json"
    }

    payload = {
        "engagement": {
            "active":    True,
            "type":      "NOTE",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
        },
        "associations": {
            "contactIds": [int(req.contact_id)],
            "companyIds": [],
            "dealIds":    [],
            "ownerIds":   []
        },
        "metadata": {
            "body": req.note
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{HUBSPOT_API_BASE}/engagements/v1/engagements",
            headers=headers,
            json=payload
        )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=f"HubSpot API error: {response.text}"
        )

    data = response.json()
    return {
        "success":       True,
        "engagement_id": data.get("engagement", {}).get("id"),
        "contact_id":    req.contact_id,
        "written_at":    datetime.now(timezone.utc).isoformat()
    }


@router.get("/contacts")
async def list_contacts(limit: int = 10):
    """
    Quick sanity check — returns first N HubSpot contacts with their IDs.
    Useful for verifying contact_id values in the dashboard.
    """
    try:
        token = get_hubspot_token()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts",
            headers=headers,
            params={"limit": limit, "properties": "firstname,lastname,email,company"}
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"HubSpot API error: {response.text}"
        )

    results = response.json().get("results", [])
    return {
        "total":    len(results),
        "contacts": [
            {
                "id":      c["id"],
                "name":    f"{c['properties'].get('firstname','')} {c['properties'].get('lastname','')}".strip(),
                "email":   c["properties"].get("email", ""),
                "company": c["properties"].get("company", "")
            }
            for c in results
        ]
    }
