import random
import uuid
from datetime import datetime, timezone

PRODUCTS = [
    {"id": "PRD-001", "name": "ProSound Elite Headphones", "price": 299.99, "sku": "AUD-PRO-001"},
    {"id": "PRD-002", "name": "Studio Monitor Speakers",   "price": 549.99, "sku": "AUD-STD-002"},
    {"id": "PRD-003", "name": "Portable DAC Amplifier",    "price": 149.99, "sku": "AUD-DAC-003"},
    {"id": "PRD-004", "name": "Premium Audio Cable Set",   "price":  49.99, "sku": "AUD-CAB-004"},
]

PRODUCT_BY_SKU = {p["sku"]: p for p in PRODUCTS}
FIRST_NAMES    = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Drew"]
LAST_NAMES     = ["Chen", "Smith", "Patel", "Johnson", "Garcia", "Kim", "Brown", "Osei"]
CUSTOMER_TYPES = ["new", "returning", "vip"]


class ShopifySimulator:

    def __init__(self):
        self._order_counter = 10000
        self.order_log: list = []
        self.metrics: dict = {
            "total_orders":        0,
            "total_revenue":       0.0,
            "new_customers":       0,
            "returning_customers": 0,
            "vip_customers":       0,
            "refunds":             0,
            "refund_amount":       0.0,
            "top_products":        {},
            "last_order_at":       None
        }

    def generate_order(self, customer_type: str = None, product_sku: str = None) -> dict:
        self._order_counter += 1
        product = PRODUCT_BY_SKU.get(product_sku, random.choice(PRODUCTS))
        ctype   = customer_type if customer_type in CUSTOMER_TYPES else random.choice(CUSTOMER_TYPES)
        qty      = random.randint(1, 3)
        subtotal = round(product["price"] * qty, 2)
        tax      = round(subtotal * 0.08, 2)
        total    = round(subtotal + tax, 2)

        return {
            "id":               f"ORD-{self._order_counter}",
            "shopify_order_id": f"gid://shopify/Order/{self._order_counter}",
            "created_at":       datetime.now(timezone.utc).isoformat(),
            "financial_status":   "paid",
            "fulfillment_status": "unfulfilled",
            "customer": {
                "id":         f"CUST-{random.randint(1000,9999)}",
                "email":      f"customer{self._order_counter}@example.com",
                "first_name": random.choice(FIRST_NAMES),
                "last_name":  random.choice(LAST_NAMES),
                "type":       ctype,
                "orders_count": (
                    random.randint(5, 25) if ctype == "vip"
                    else random.randint(2, 5) if ctype == "returning"
                    else 1
                ),
                "total_spent": str(
                    round(random.uniform(500, 2500), 2) if ctype == "vip"
                    else round(random.uniform(50, 450), 2)
                )
            },
            "line_items": [{
                "product_id":  product["id"],
                "sku":         product["sku"],
                "title":       product["name"],
                "quantity":    qty,
                "price":       str(product["price"]),
                "total_price": str(subtotal)
            }],
            "subtotal_price": str(subtotal),
            "total_tax":      str(tax),
            "total_price":    str(total),
            "currency":       "USD",
            "tags":           [ctype, product["sku"].split("-")[1].lower()]
        }

    def generate_refund(self, order: dict) -> dict:
        return {
            "id":              f"REF-{uuid.uuid4().hex[:8].upper()}",
            "order_id":        order["id"],
            "created_at":      datetime.now(timezone.utc).isoformat(),
            "refund_line_items": order["line_items"],
            "total_refunded":  order["total_price"],
            "reason":          random.choice(["customer_request", "defective", "other"])
        }

    def record_order(self, order: dict) -> None:
        self.order_log.insert(0, order)
        if len(self.order_log) > 500:
            self.order_log.pop()
        ctype = order["customer"]["type"]
        self.metrics["total_orders"]  += 1
        self.metrics["total_revenue"] += float(order["total_price"])
        self.metrics["last_order_at"]  = order["created_at"]
        if ctype == "new":
            self.metrics["new_customers"]       += 1
        elif ctype == "returning":
            self.metrics["returning_customers"] += 1
        elif ctype == "vip":
            self.metrics["vip_customers"]       += 1
        sku = order["line_items"][0]["sku"]
        self.metrics["top_products"][sku] = self.metrics["top_products"].get(sku, 0) + 1

    def record_refund(self, refund: dict) -> None:
        self.metrics["refunds"]       += 1
        self.metrics["refund_amount"] += float(refund["total_refunded"])

    def get_status(self) -> dict:
        top = sorted(self.metrics["top_products"].items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "total_orders_logged": len(self.order_log),
            "metrics": {
                **self.metrics,
                "total_revenue": round(self.metrics["total_revenue"], 2),
                "refund_amount": round(self.metrics["refund_amount"], 2),
                "net_revenue":   round(self.metrics["total_revenue"] - self.metrics["refund_amount"], 2),
                "top_products":  [{"sku": s, "order_count": c} for s, c in top]
            }
        }

    def reset(self) -> None:
        self.__init__()
