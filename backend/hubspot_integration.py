import requests
import os
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
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json"
        }

    def search_company_by_name(self, company_name: str) -> str | None:
        """Search HubSpot for an existing company by name. Returns company ID or None."""
        url = self.base_url + "/crm/v3/objects/companies/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "name",
                    "operator": "EQ",
                    "value": company_name
                }]
            }],
            "properties": ["name"],
            "limit": 1
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                company_id = results[0]["id"]
                print("  Found existing company: " + company_name + " ID: " + company_id)
                return company_id
            return None
        except Exception as e:
            print("  Company search failed for " + company_name + ": " + str(e))
            return None

    def get_or_create_company(self, account: Dict) -> str | None:
        """Find existing company by name, or create if not found."""
        company_name = account["company_name"]

        # 1. Search first
        existing_id = self.search_company_by_name(company_name)
        if existing_id:
            return existing_id

        # 2. Create only if not found
        result = self.create_company(account)
        if result["success"]:
            return result["company_id"]

        return None

    def create_company(self, account: Dict) -> Dict:
        url = self.base_url + "/crm/v3/objects/companies"
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
            company_id = response.json()["id"]
            print("Created company: " + account["company_name"] + " ID: " + company_id)
            return {"success": True, "company_id": company_id}
        except requests.exceptions.RequestException as e:
            print("Failed to create company " + account["company_name"] + ": " + str(e))
            return {"success": False, "error": str(e)}

    def get_or_create_contact(self, account: Dict, company_id: str) -> str:
        contact = account["contact"]
        email = contact["email"]
        search_url = self.base_url + "/crm/v3/objects/contacts/search"
        search_payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                }]
            }],
            "properties": ["email", "firstname", "lastname"]
        }
        try:
            response = requests.post(search_url, json=search_payload, headers=self.headers)
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                contact_id = results[0]["id"]
                print("  Found existing contact: " + contact["name"] + " ID: " + contact_id)
                self.associate_contact_to_company(contact_id, company_id)
                return contact_id
        except Exception as e:
            print("  Contact search failed: " + str(e))
        url = self.base_url + "/crm/v3/objects/contacts"
        name_parts = contact["name"].split()
        firstname = name_parts[0]
        lastname = name_parts[-1] if len(name_parts) > 1 else name_parts[0]
        payload = {
            "properties": {
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "jobtitle": contact["title"],
                "lifecyclestage": "lead",
            }
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            contact_id = response.json()["id"]
            self.associate_contact_to_company(contact_id, company_id)
            print("  Created contact: " + contact["name"] + " ID: " + contact_id)
            return contact_id
        except Exception as e:
            print("  Could not get or create contact " + contact["name"] + ": " + str(e))
            return None

    def associate_contact_to_company(self, contact_id: str, company_id: str):
        url = self.base_url + "/crm/v4/objects/contacts/" + contact_id + "/associations/companies/" + company_id
        payload = [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 279}]
        try:
            r = requests.put(url, json=payload, headers=self.headers)
            print("  Association status: " + str(r.status_code) + " contact " + contact_id + " -> company " + company_id)
        except Exception as e:
            print("  Association error: " + str(e))

    def get_contacts_for_company(self, company_id: str) -> List[str]:
        url = self.base_url + "/crm/v3/objects/companies/" + company_id + "/associations/contacts"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            results = response.json().get("results", [])
            contact_ids = [r["id"] for r in results]
            print("  Found " + str(len(contact_ids)) + " contact(s) for company " + company_id)
            return contact_ids
        except Exception as e:
            print("  Could not fetch contacts for company " + company_id + ": " + str(e))
            return []

    def log_behavior_activity(self, contact_id: str, behavior: Dict, company_id: str = None) -> bool:
        action_text = behavior.get("action", "unknown").replace("_", " ").title()
        note_body = (
            "[ABM Behavior] " + action_text + ": " +
            behavior.get("product_name", "Unknown") + " (" +
            behavior.get("product_sku", "N/A") + ") - Score: " +
            str(behavior.get("engagement_score", 0))
        )
        note_url = self.base_url + "/crm/v3/objects/notes"
        payload = {
            "properties": {
                "hs_note_body": note_body,
                "hs_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            }
        }
        try:
            response = requests.post(note_url, json=payload, headers=self.headers)
            response.raise_for_status()
            note_id = response.json()["id"]
            print("  Note created " + note_id + ": " + action_text)
        except Exception as e:
            print("  Failed to create note: " + str(e))
            return False
        if contact_id:
            assoc_url = self.base_url + "/crm/v3/associations/notes/contacts/batch/create"
            assoc_payload = {"inputs": [{"from": {"id": note_id}, "to": {"id": contact_id}, "type": "note_to_contact"}]}
            try:
                r = requests.post(assoc_url, json=assoc_payload, headers=self.headers)
                r.raise_for_status()
                print("  Note " + note_id + " -> contact " + contact_id)
            except Exception as e:
                print("  Contact association failed: " + str(e))
        if company_id:
            assoc_url = self.base_url + "/crm/v3/associations/notes/companies/batch/create"
            assoc_payload = {"inputs": [{"from": {"id": note_id}, "to": {"id": company_id}, "type": "note_to_company"}]}
            try:
                r = requests.post(assoc_url, json=assoc_payload, headers=self.headers)
                r.raise_for_status()
                print("  Note " + note_id + " -> company " + company_id)
            except Exception as e:
                print("  Company association failed: " + str(e))
        return True

    def update_company_engagement(self, company_id: str, engagement:
        url = self.base_url + "/crm/v3/objects/companies/" + company_id
        payload = {
            "properties": {
                "description": "ABM Score: " + str(engagement_data.get("total_engagement_score", 0)) + " Interactions: " + str(engagement_data.get("interaction_count", 0))
            }
        }
        try:
            response = requests.patch(url, json=payload, headers=self.headers)
            response.raise_for_status()
            print("  Updated engagement for company " + company_id)
            return True
        except requests.exceptions.RequestException as e:
            print("  Failed to update company " + company_id + ": " + str(e))
            return False

if __name__ == "__main__":
    api_key = os.getenv("HUBSPOT_API_KEY", "")
    hs = HubSpotIntegration(api_key)
    print("HubSpot integration ready!")
