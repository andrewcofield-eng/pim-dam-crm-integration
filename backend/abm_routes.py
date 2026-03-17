from fastapi import APIRouter, HTTPException
import httpx
import json
from orchestrator import ABMSimulationOrchestrator
from accounts import ACCOUNTS
from openai import OpenAI
import os

router = APIRouter(prefix="/abm", tags=["ABM"])

_orchestrator = None

def get_orchestrator(directus_url: str):
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ABMSimulationOrchestrator(
            hubspot_api_key=os.getenv("HUBSPOT_API_KEY"),
            directus_url=directus_url,
            directus_token=None
        )
    return _orchestrator

@router.get("/warm-prospects")
async def get_warm_prospects(directus_url: str, directus_token: str):
    """Get warm ABM prospects"""
    try:
        orchestrator = get_orchestrator(directus_url)
        orchestrator.directus_token = directus_token
        warm_prospects = await orchestrator.get_warm_prospects()
        
        total_pipeline = sum(
            float(p["account_value"].replace("potential $", "").replace("K annual", "").strip()) * 1000
            for p in warm_prospects
        )
        
        return {
            "status": "success",
            "warm_prospects_count": len(warm_prospects),
            "prospects": warm_prospects,
            "total_pipeline_value": f""
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaign/generate")
async def generate_abm_campaign(account_id: str, directus_url: str, directus_token: str):
    """Generate personalized ABM campaign for a specific account"""
    try:
        account = None
        for acc in ACCOUNTS:
            if acc["id"] == account_id:
                account = acc
                break
        
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
        
        headers = {"Authorization": f"Bearer {directus_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{directus_url}/items/products",
                headers=headers
            )
        products = response.json()["data"]
        
        interested_products = [
            p for p in products
            if p.get("category") in account.get("interested_categories", [])
        ][:3]
        
        product_context = json.dumps([
            {
                "sku": p["sku"],
                "name": p["product_name"],
                "category": p["category"],
                "price": p["price"]
            }
            for p in interested_products
        ])
        
        prompt = (
            f"You are an ABM strategist. Create a personalized campaign for this B2B prospect:\\n\\n"
            f"Company: {account['company_name']}\\n"
            f"Industry: {account['industry']}\\n"
            f"Size: {account['company_size']} ({account['employees']} employees)\\n"
            f"Revenue: {account['annual_revenue']}\\n"
            f"Use Case: {account['use_case']}\\n"
            f"Pain Point: {account['pain_point']}\\n"
            f"Buying Stage: {account['buying_stage']}\\n"
            f"Key Contact: {account['contact']['name']} ({account['contact']['title']})\\n\\n"
            f"Products:\\n{product_context}\\n\\n"
            f"Generate:\\n"
            f"1. ACCOUNT INSIGHT\\n"
            f"2. PERSONALIZED BUNDLE\\n"
            f"3. EMAIL SUBJECT\\n"
            f"4. EMAIL BODY\\n"
            f"5. EXECUTIVE SUMMARY\\n"
            f"6. NEXT STEPS"
        )
        
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        message = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert ABM strategist for B2B apparel partnerships."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return {
            "account_id": account_id,
            "company_name": account["company_name"],
            "campaign_type": "ABM",
            "contact": account["contact"],
            "campaign": message.choices[0].message.content,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup-accounts")
async def setup_abm_accounts(directus_url: str, directus_token: str):
    """Create all 10 B2B accounts in HubSpot"""
    try:
        orchestrator = get_orchestrator(directus_url)
        orchestrator.directus_token = directus_token
        accounts_map = await orchestrator.setup_accounts_in_hubspot()
        
        return {
            "status": "success",
            "message": f"Created {len(accounts_map)} accounts in HubSpot",
            "accounts_created": len(accounts_map),
            "accounts": accounts_map
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate-behaviors")
async def simulate_and_log_behaviors(directus_url: str, directus_token: str, days: int = 7):
    """Simulate account behaviors and log to HubSpot"""
    try:
        orchestrator = get_orchestrator(directus_url)
        orchestrator.directus_token = directus_token
        
        # Run simulation and log all behaviors to HubSpot
        behaviors = await orchestrator.simulate_all_behaviors(days=days)
        
        return {
            "status": "success",
            "message": f"Simulated behaviors for {len(behaviors)} accounts and logged to HubSpot",
            "accounts_simulated": len(behaviors),
            "total_behaviors": sum(len(b) for b in behaviors.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

