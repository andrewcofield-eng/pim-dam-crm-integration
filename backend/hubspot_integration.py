import requests
import os
import json
from typing import Dict, List
from datetime import datetime

INDUSTRY_MAP = {
    "Outdoor Apparel Retail": "RETAIL",
    "Fitness Chain": "HEALTH_WELLNESS_AND_FITNESS",
    "Corporate Merchandise": "CONSUMER_GOODS",
    "Adventure Travel": "LEISURE_TRAVEL_TOURISM",
    "Fashion Retail": "RETAIL",
    "Employee Benefits": "HUMAN_RESOURCES",
    "Event Management": "EVENTS_SERVICES",
    "College Merchandise": "RETAIL",
    "Non-Profit": "NON_PROFIT_ORGANIZATION_MANAGEMENT",
    "Hospitality": "HOSPITALITY"
}

LIFECYCLE_MAP = {
    "awareness": "lead",
    "consideration": "marketingqualifiedlead",
    "negotiation": "salesqualifiedlead",
    "early awareness": "subscriber"
}

class HubSpotIntegration:
    """Integrate behavior simulator with real HubSpot CRM"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def create_company(self, account: Dict) -> Dict:
        """Create a company in HubSpot from account data"""
        url = f"{self.base_url}/crm/v3/objects/companies"

        # Clean annual revenue - remove M/K and convert to number
        revenue_str = str(account.get("annual_revenue", "0"))
        if "M" in revenue_str:
            revenue = float(revenue_str.replace("M", "")) * 1000000
        elif "K" in revenue_str:
            revenue = float(revenue_str.replace("K", "")) * 1000
        else:
            revenue = float(revenue_str) if revenue_str.isdigit() else 0

        industry = INDUSTRY_MAP.get(account.get("industry", ""), "RETAIL")
        lifecycle = LIFECYCLE_MAP.get(account.get("buying_stage", "awareness"), "lead")

        payload = {
            "properties": {
                "name": account["company_name"],
                "industry": industry,
                "numberofemployees": str(account.get("employees", 0)),
                "annualrevenue": str(int(revenue)),
                "lifecyclestage": lifecycle,
                "description": account.get("use_case", ""),
            }
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            company_id = result["id"]
            print(f"✅ Created company: {account['company_name']} (ID: {company_id})")
            return {
                "success": True,
                "company_id": company_id,
                "company_name": account["company_name"]
            }
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to create company {account['company_name']}: {str(e)}")
            try:
                print(f"   Detail: {e.response.json()}")
            except:
                pass
            return {"success": False, "error": str(e)}

    def create_contact(self, account: Dict, company_id: str) -> Dict:
        """Create a contact in HubSpot for the account"""
        url = f"{self.base_url}/crm/v3/objects/contacts"

        contact = account["contact"]
        name_parts = contact["name"].split()
        firstname = name_parts[0]
        lastname = name_parts[-1] if len(name_parts) > 1 else name_parts[0]

        payload = {
            "properties": {
                "firstname": firstname,
                "lastname": lastname,
                "email": contact["email"],
                "jobtitle": contact["title"],
                "lifecyclestage": "lead",
            }
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            contact_id = result["id"]
            self.associate_contact_to_company(contact_id, company_id)
            print(f"✅ Created contact: {contact['name']} (ID: {contact_id})")
            return {"success": True, "contact_id": contact_id}
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to create contact {contact['name']}: {str(e)}")
            return {"success": False, "error": str(e)}

    def associate_contact_to_company(self, contact_id: str, company_id: str):
        """Associate a contact with a company"""
        url = f"{self.base_url}/crm/v4/objects/contacts/{contact_id}/associations/companies/{company_id}"
        payload = [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 279}]
        try:
            requests.put(url, json=payload, headers=self.headers)
        except:
            pass

    def update_company_engagement(self, company_id: str, engagement_data: Dict) -> bool:
        """Update company with engagement score and warm prospect status"""
        url = f"{self.base_url}/crm/v3/objects/companies/{company_id}"

        lifecycle = "marketingqualifiedlead" if engagement_data.get("warm_prospect") else "lead"

        payload = {
            "properties": {
                "lifecyclestage": lifecycle,
                "hs_analytics_num_page_views": str(engagement_data.get("interaction_count", 0)),
            }
        }

        try:
            requests.patch(url, json=payload, headers=self.headers)
            print(f"✅ Updated engagement for company {company_id}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to update company: {str(e)}")
            return False

    def log_behavior_activity(self, behavior: Dict, company_id: str, contact_id: str) -> bool:
        """Log a behavior event as a HubSpot note"""
        url = f"{self.base_url}/crm/v3/objects/notes"

        note_body = f"[ABM Behavior] {behavior['action'].replace('_', ' ').title()}: {behavior['product_name']} ({behavior['product_sku']}) - Score: {behavior['engagement_score']}"

        payload = {
            "properties": {
                "hs_note_body": note_body,
                "hs_timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return True
        except:
            return False

if __name__ == "__main__":
    api_key = os.getenv("HUBSPOT_API_KEY", "")
    hs = HubSpotIntegration(api_key)
    print("HubSpot integration ready!")




