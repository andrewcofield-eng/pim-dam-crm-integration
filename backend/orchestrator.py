import asyncio
import json
from typing import List, Dict
from simulator import BehaviorSimulator
from hubspot_integration import HubSpotIntegration
from accounts import ACCOUNTS
import httpx

class ABMSimulationOrchestrator:
    """Orchestrates behavior simulation and CRM logging"""

    def __init__(self, hubspot_api_key: str, directus_url: str, directus_token: str):
        self.simulator = BehaviorSimulator()
        self.hubspot = HubSpotIntegration(hubspot_api_key)
        self.directus_url = directus_url
        self.directus_token = directus_token
        self.accounts_map = {}

    async def fetch_products_from_directus(self) -> List[Dict]:
        """Fetch all products from live Directus"""
        headers = {"Authorization": f"Bearer {self.directus_token}"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.directus_url}/items/products", headers=headers)
                products = response.json()["data"]
                print(f"Fetched {len(products)} products from Directus")
                return products
        except Exception as e:
            print(f"Failed to fetch products: {str(e)}")
            return []

    async def setup_accounts_in_hubspot(self) -> Dict[str, str]:
        """Create all B2B accounts in HubSpot"""
        print("Setting up accounts in HubSpot...")
        for account in ACCOUNTS:
            company_result = self.hubspot.create_company(account)
            if company_result["success"]:
                company_id = company_result["company_id"]
                self.accounts_map[account["id"]] = company_id
                self.hubspot.get_or_create_contact(account, company_id)
            await asyncio.sleep(0.5)
        print(f"Created {len(self.accounts_map)} accounts in HubSpot")
        return self.accounts_map

    async def simulate_all_behaviors(self, days: int = 7) -> Dict:
        """Simulate behavior for all accounts"""
        print(f"Simulating behaviors for {len(ACCOUNTS)} accounts over {days} days...")
        products = await self.fetch_products_from_directus()
        if not products:
            return {}
        all_behaviors = {}
        for account in ACCOUNTS:
            behaviors = self.simulator.simulate_account_behavior(account, products, days=days)
            all_behaviors[account["id"]] = behaviors
            company_id = self.accounts_map.get(account["id"])
            if company_id and behaviors:
                contact_ids = self.hubspot.get_contacts_for_company(company_id)
                for behavior in behaviors:
                    for contact_id in contact_ids:
                        self.hubspot.log_behavior_activity(contact_id, behavior, company_id=company_id)
                engagement = self.simulator.aggregate_account_engagement(behaviors)
                self.hubspot.update_company_engagement(company_id, engagement)
            await asyncio.sleep(0.3)
        return all_behaviors

    async def get_warm_prospects(self) -> List[Dict]:
        """Get accounts that are warm prospects"""
        print("Identifying warm prospects...")
        products = await self.fetch_products_from_directus()
        warm_prospects = []
        for account in ACCOUNTS:
            behaviors = self.simulator.simulate_account_behavior(account, products, days=14)
            engagement = self.simulator.aggregate_account_engagement(behaviors)
            if engagement.get("warm_prospect"):
                warm_prospects.append({
                    "account_id": account["id"],
                    "company_name": account["company_name"],
                    "industry": account["industry"],
                    "contact": account["contact"],
                    "engagement_score": engagement["total_engagement_score"],
                    "interaction_count": engagement["interaction_count"],
                    "account_value": account["account_value"],
                    "buying_stage": account["buying_stage"],
                    "actions": engagement["actions"],
                })
        warm_prospects.sort(key=lambda x: x["engagement_score"], reverse=True)
        print(f"Found {len(warm_prospects)} warm prospects")
        return warm_prospects

async def main():
    hubspot_api_key = "YOUR_KEY"
    directus_url = "https://directus-production-9f53.up.railway.app"
    directus_token = "YOUR_TOKEN"
    orchestrator = ABMSimulationOrchestrator(hubspot_api_key, directus_url, directus_token)
    await orchestrator.setup_accounts_in_hubspot()
    behaviors = await orchestrator.simulate_all_behaviors(days=7)
    warm = await orchestrator.get_warm_prospects()
    print(json.dumps([w for w in warm[:3]], indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())



