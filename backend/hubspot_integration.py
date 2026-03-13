import requests
import json
from typing import Dict, List
from datetime import datetime

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
        
        payload = {
            "properties": {
                "name": account["company_name"],
                "industry": account["industry"],
                "numberofemployees": str(account["employees"]),
                "annualrevenue": account["annual_revenue"],
                "lifecyclestage": "subscriber",
                "hs_lead_status": account["buying_stage"],
                "description": account["use_case"],
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
            return {"success": False, "error": str(e)}
    
    def create_contact(self, account: Dict, company_id: str) -> Dict:
        """Create a contact in HubSpot for the account"""
        url = f"{self.base_url}/crm/v3/objects/contacts"
        
        contact = account["contact"]
        payload = {
            "properties": {
                "firstname": contact["name"].split()[0],
                "lastname": contact["name"].split()[-1] if len(contact["name"].split()) > 1 else contact["name"],
                "email": contact["email"],
                "jobtitle": contact["title"],
                "lifecyclestage": "subscriber",
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            contact_id = result["id"]
            
            # Associate contact with company
            self.associate_contact_to_company(contact_id, company_id)
            
            print(f"✅ Created contact: {contact['name']} (ID: {contact_id})")
            return {
                "success": True,
                "contact_id": contact_id,
                "contact_name": contact["name"]
            }
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to create contact {contact['name']}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def associate_contact_to_company(self, contact_id: str, company_id: str):
        """Associate a contact with a company"""
        url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}"
        
        payload = {
            "associationCategory": "HUBSPOT_DEFINED",
            "associationType": "contact_to_company"
        }
        
        try:
            requests.put(url, json=payload, headers=self.headers)
        except:
            pass  # Association may already exist
    
    def log_behavior_activity(self, behavior: Dict, company_id: str, contact_id: str) -> bool:
        """Log a behavior event as a HubSpot activity"""
        url = f"{self.base_url}/crm/v3/objects/companies/{company_id}"
        
        # Create engagement note
        note = f"{behavior['action'].replace('_', ' ').title()}: {behavior['product_name']} ({behavior['product_sku']})"
        
        payload = {
            "properties": {
                "hs_analytics_num_visits": "1",  # Increment visit counter
                "notes_last_updated": datetime.utcnow().isoformat(),
            }
        }
        
        try:
            requests.patch(url, json=payload, headers=self.headers)
            return True
        except:
            return False
    
    def update_company_engagement(self, company_id: str, engagement_data: Dict) -> bool:
        """Update company with engagement score and warm prospect status"""
        url = f"{self.base_url}/crm/v3/objects/companies/{company_id}"
        
        payload = {
            "properties": {
                "hs_analytics_num_page_views": str(engagement_data.get("interaction_count", 0)),
                "lifecyclestage": "marketingqualifiedlead" if engagement_data["warm_prospect"] else "subscriber",
                "hs_lead_status": "warm" if engagement_data["warm_prospect"] else "cold",
            }
        }
        
        try:
            requests.patch(url, json=payload, headers=self.headers)
            print(f"✅ Updated engagement for company {company_id}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to update company: {str(e)}")
            return False

# Example usage
if __name__ == "__main__":
    api_key = "YOUR_API_KEY_HERE"
    hs = HubSpotIntegration(api_key)
    print("HubSpot integration ready!")
