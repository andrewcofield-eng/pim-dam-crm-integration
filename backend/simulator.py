import random
from datetime import datetime, timedelta
from typing import List, Dict
import json

class BehaviorSimulator:
    """Simulates realistic B2B account behavior on UrbanThread"""
    
    def __init__(self):
        # Behavior patterns based on buying stage
        self.behavior_patterns = {
            "awareness": {
                "view_product": 0.4,
                "download_spec": 0.1,
                "email_open": 0.2,
            },
            "consideration": {
                "view_product": 0.7,
                "download_spec": 0.4,
                "email_open": 0.5,
                "add_to_cart": 0.2,
            },
            "negotiation": {
                "view_product": 0.8,
                "download_spec": 0.6,
                "email_open": 0.7,
                "add_to_cart": 0.5,
                "request_quote": 0.3,
            }
        }
        
        # Engagement scoring
        self.action_scores = {
            "view_product": 5,
            "download_spec": 15,
            "email_open": 10,
            "email_click": 25,
            "add_to_cart": 40,
            "request_quote": 60,
            "schedule_call": 100,
        }
    
    def simulate_account_behavior(self, account: Dict, products: List[Dict], days: int = 7) -> List[Dict]:
        """
        Simulate behavior for an account over N days.
        Returns list of behavior events.
        """
        behaviors = []
        buying_stage = account.get("buying_stage", "awareness")
        interested_categories = account.get("interested_categories", [])
        
        # Filter products to account's interests
        relevant_products = [
            p for p in products 
            if p.get("category") in interested_categories
        ]
        
        if not relevant_products:
            relevant_products = products
        
        # Simulate daily behaviors
        for day in range(days):
            event_date = datetime.utcnow() - timedelta(days=days-day-1)
            
            # Based on buying stage, determine what actions happen
            stage_patterns = self.behavior_patterns.get(buying_stage, {})
            
            for action, probability in stage_patterns.items():
                if random.random() < probability:
                    # This action happens
                    product = random.choice(relevant_products)
                    
                    behavior = {
                        "account_id": account["id"],
                        "company_name": account["company_name"],
                        "action": action,
                        "product_sku": product["sku"],
                        "product_name": product["product_name"],
                        "category": product["category"],
                        "timestamp": event_date.isoformat(),
                        "engagement_score": self.action_scores.get(action, 0),
                        "buying_stage": buying_stage,
                    }
                    behaviors.append(behavior)
        
        return behaviors
    
    def aggregate_account_engagement(self, behaviors: List[Dict]) -> Dict:
        """Calculate total engagement score for an account from behaviors"""
        if not behaviors:
            return {
                "total_engagement_score": 0,
                "interaction_count": 0,
                "actions": {}
            }
        
        account_id = behaviors[0]["account_id"]
        total_score = sum(b["engagement_score"] for b in behaviors)
        action_counts = {}
        
        for behavior in behaviors:
            action = behavior["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            "account_id": account_id,
            "total_engagement_score": total_score,
            "interaction_count": len(behaviors),
            "actions": action_counts,
            "last_interaction": max(b["timestamp"] for b in behaviors),
            "warm_prospect": total_score > 50,  # Threshold for "warm"
        }

# Example usage
if __name__ == "__main__":
    from accounts import ACCOUNTS
    
    # Mock products for testing
    mock_products = [
        {"sku": "TOP-001", "product_name": "Classic Crew Tee", "category": "T-Shirts"},
        {"sku": "HOD-001", "product_name": "Pullover Fleece Hoodie", "category": "Hoodies"},
        {"sku": "OUT-001", "product_name": "Packable Rain Jacket", "category": "Outerwear"},
    ]
    
    simulator = BehaviorSimulator()
    
    # Simulate behavior for first account
    account = ACCOUNTS[0]
    behaviors = simulator.simulate_account_behavior(account, mock_products, days=7)
    engagement = simulator.aggregate_account_engagement(behaviors)
    
    print(json.dumps(engagement, indent=2))
