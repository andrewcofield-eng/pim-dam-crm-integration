"""
shopify_simulator.py — Persisted to JSON file for survival across redeploys
"""
import json
import random
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

# Persist to a file in the project root (Railway allows file writes)
DATA_FILE = os.path.join(os.path.dirname(__file__), "shopify_data.json")

class ShopifySimulator:
    def __init__(self):
        self.order_log: List[dict] = []
        self.metrics = {
            "total_orders": 0,
            "total_revenue": 0.0,
            "new_customers": 0,
            "returning_customers": 0,
            "vip_customers": 0,
            "refunds": 0,
            "refund_amount": 0.0,
            "top_products": [],
            "last_order_at": None,
            "net_revenue": 0.0
        }
        self._load_from_disk()

    def _load_from_disk(self):
        """Load persisted data from JSON file if it exists."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.order_log = data.get("order_log", [])
                    self.metrics = data.get("metrics", self.metrics)
                print(f"[Shopify] Loaded {len(self.order_log)} orders from disk")
            except Exception as e:
                print(f"[Shopify] Failed to load from disk: {e}")

    def _save_to_disk(self):
        """Persist current state to JSON file."""
        try:
            data = {
                "order_log": self.order_log,
                "metrics": self.metrics,
                "saved_at": datetime.now(timezone.utc).isoformat()
            }
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"[Shopify] Failed to save to disk: {e}")

    def generate_order(self, customer_type: Optional[str] = None, product_sku: Optional[str] = None) -> dict:
        """Generate a realistic Shopify order."""
        customer_types = ["new", "returning", "vip"]
        ct = customer_type or random.choice(customer_types)
        
        skus = ["TOP-001", "TOP-002", "HOD-001", "HOD-002", "DNM-001", "DNM-002", "OUT-001", "OUT-002", "ACC-001", "ACC-002"]
        sku = product_sku or random.choice(skus)
        
        base_prices = {
            "TOP-001": 24.99, "TOP-002": 34.99,
            "HOD-001": 64.99, "HOD-002": 79.99,
            "DNM-001": 89.99, "DNM-002": 99.99,
            "OUT-001": 119.99, "OUT-002": 94.99,
            "ACC-001": 34.99, "ACC-002": 22.99
        }
        
        price = base_prices.get(sku, 49.99)
        if ct == "vip":
            price = round(price * 1.2, 2)  # VIP buys premium variants
        
        qty = random.randint(1, 3)
        subtotal = round(price * qty, 2)
        tax = round(subtotal * 0.08, 2)
        shipping = 0 if subtotal > 100 else 9.99
        total = round(subtotal + tax + shipping, 2)
        
        order = {
            "id": f"ORD-{random.randint(100000, 999999)}",
            "sku": sku,
            "customer_type": ct,
            "quantity": qty,
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping,
            "total": total,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        return order

    def record_order(self, order: dict):
        """Record an order and update metrics."""
        self.order_log.insert(0, order)
        
        # Update metrics
        self.metrics["total_orders"] += 1
        self.metrics["total_revenue"] = round(self.metrics["total_revenue"] + order["total"], 2)
        self.metrics["net_revenue"] = round(self.metrics["total_revenue"] - self.metrics["refund_amount"], 2)
        self.metrics["last_order_at"] = order["created_at"]
        
        ct = order["customer_type"]
        if ct == "new":
            self.metrics["new_customers"] += 1
        elif ct == "returning":
            self.metrics["returning_customers"] += 1
        elif ct == "vip":
            self.metrics["vip_customers"] += 1
        
        # Update top products
        sku = order["sku"]
        existing = next((p for p in self.metrics["top_products"] if p["sku"] == sku), None)
        if existing:
            existing["order_count"] += 1
        else:
            self.metrics["top_products"].append({"sku": sku, "order_count": 1})
        
        # Sort top products by count
        self.metrics["top_products"].sort(key=lambda x: x["order_count"], reverse=True)
        
        # Persist to disk after every order
        self._save_to_disk()

    def generate_bulk_orders(self, count: int = 10) -> List[dict]:
        """Generate multiple orders at once."""
        orders = []
        for _ in range(count):
            o = self.generate_order()
            self.record_order(o)
            orders.append(o)
        return orders

    def get_status(self) -> dict:
        """Return current simulator status."""
        return {
            "status": "active",
            "total_orders_logged": len(self.order_log),
            "metrics": self.metrics,
            "persistence": "file-based",
            "data_file": DATA_FILE
        }

    def get_metrics(self) -> dict:
        """Return just the metrics."""
        return self.metrics

    def reset(self):
        """Clear all data (for testing)."""
        self.order_log = []
        self.metrics = {
            "total_orders": 0,
            "total_revenue": 0.0,
            "new_customers": 0,
            "returning_customers": 0,
            "vip_customers": 0,
            "refunds": 0,
            "refund_amount": 0.0,
            "top_products": [],
            "last_order_at": None,
            "net_revenue": 0.0
        }
        self._save_to_disk()
        return {"message": "Simulator reset, data cleared"}