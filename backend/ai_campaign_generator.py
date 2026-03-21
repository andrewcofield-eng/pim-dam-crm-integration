import os
import json
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SEGMENTS = {
    "seg_001": {
        "segment_id":         "seg_001",
        "name":               "High-Value Repeat Buyers",
        "size":               2847,
        "avg_order_value":    284.50,
        "top_categories":     ["Electronics", "Premium Audio"],
        "purchase_frequency": "monthly",
        "churn_risk":         "low",
        "hubspot_list_id":    "hs_list_4421"
    },
    "seg_002": {
        "segment_id":         "seg_002",
        "name":               "At-Risk Subscribers",
        "size":               1203,
        "avg_order_value":    142.00,
        "top_categories":     ["Audio Accessories", "Budget Audio"],
        "purchase_frequency": "quarterly",
        "churn_risk":         "high",
        "hubspot_list_id":    "hs_list_4422"
    },
    "seg_003": {
        "segment_id":         "seg_003",
        "name":               "New Customer Acquisition",
        "size":               8921,
        "avg_order_value":    89.99,
        "top_categories":     ["Entry-Level Audio", "Cables"],
        "purchase_frequency": "one-time",
        "churn_risk":         "medium",
        "hubspot_list_id":    "hs_list_4423"
    }
}

PRODUCTS = [
    {
        "sku":          "TOP-001",
        "name":         "Classic Crew Tee",
        "price":        24.99,
        "category":     "T-Shirts",
        "key_features": ["100% ring-spun cotton", "Pre-shrunk", "XS to 3XL sizing"],
        "stock_status": "in_stock",
        "margin":       "medium"
    },
    {
        "sku":          "HOD-001",
        "name":         "Pullover Fleece Hoodie",
        "price":        64.99,
        "category":     "Hoodies",
        "key_features": ["380gsm fleece", "Kangaroo pocket", "Brushed interior"],
        "stock_status": "in_stock",
        "margin":       "high"
    },
    {
        "sku":          "DNM-001",
        "name":         "Slim Fit Jeans",
        "price":        89.99,
        "category":     "Denim",
        "key_features": ["12oz selvedge denim", "Mid-rise tapered leg", "Broken-in feel"],
        "stock_status": "in_stock",
        "margin":       "high"
    }
]
SEGMENT_PRODUCT_MAP = {
    "seg_001": "TOP-001",
    "seg_002": "HOD-001",
    "seg_003": "DNM-001",
}

def build_unified_payload(segment_id: str, override_goals: dict = None) -> dict:
    segment = SEGMENTS.get(segment_id, SEGMENTS["seg_001"])
    target_sku = SEGMENT_PRODUCT_MAP.get(segment_id, "TOP-001")
    product = next((p for p in PRODUCTS if p["sku"] == target_sku), PRODUCTS[0])
    return {
        "customer_segment": segment,
        "products":         [product],
        "brand_assets":     BRAND_ASSETS,
        "campaign_goals": {
            "objective":      "retention",
            "target_revenue": 50000,
            "timeline":       "30 days",
            "channels":       ["email", "paid_social", "landing_page"],
            **(override_goals or {})
        }
    }


def build_system_prompt(brief: dict) -> str:
    seg     = brief["customer_segment"]
    product = brief["products"][0]
    assets  = brief["brand_assets"]
    goals   = brief["campaign_goals"]
    return (
        "You are an expert marketing copywriter for a premium brand.\n\n"
        f"BRAND VOICE: {assets['tone_of_voice']}\n"
        f"COLOR PALETTE: {', '.join(assets['color_palette'])}\n\n"
        "CUSTOMER SEGMENT:\n"
        f"- Name: {seg['name']}\n"
        f"- Audience Size: {seg['size']:,} customers\n"
        f"- Avg Order Value: ${seg['avg_order_value']}\n"
        f"- Purchase Frequency: {seg['purchase_frequency']}\n"
        f"- Top Categories: {', '.join(seg['top_categories'])}\n"
        f"- Churn Risk: {seg['churn_risk']}\n\n"
        "FEATURED PRODUCT (from PIM):\n"
        f"- Name: {product['name']} (SKU: {product['sku']})\n"
        f"- Price: ${product['price']}\n"
        f"- Key Features: {', '.join(product['key_features'])}\n"
        f"- Stock Status: {product['stock_status']}\n"
        f"- Margin Tier: {product['margin']}\n\n"
        "CAMPAIGN GOALS:\n"
        f"- Objective: {goals['objective']}\n"
        f"- Target Revenue: ${goals['target_revenue']:,}\n"
        f"- Timeline: {goals['timeline']}\n"
        f"- Channels: {', '.join(goals['channels'])}\n\n"
        "Generate copy that is data-informed and segment-specific.\n"
        "Return ONLY valid JSON, no markdown, no extra text."
    )


USER_PROMPT = """{
  "email": {
    "subject_lines": ["<option1>", "<option2>", "<option3>"],
    "preview_text": "<50-char preview>",
    "headline": "<main email headline>",
    "body_copy": "<2-3 paragraph email body>",
    "cta_button": "<CTA text>",
    "ps_line": "<PS urgency line>"
  },
  "ad_headlines": {
    "google_search": ["<h1 max30>", "<h2 max30>", "<h3 max30>"],
    "meta_primary": "<primary text max125>",
    "meta_headline": "<headline max40>",
    "meta_description": "<description max30>"
  },
  "landing_page": {
    "hero_headline": "<bold hero headline>",
    "hero_subheadline": "<supporting subheadline>",
    "value_props": [
      {"icon": "<emoji>", "title": "<title>", "description": "<1 sentence>"},
      {"icon": "<emoji>", "title": "<title>", "description": "<1 sentence>"},
      {"icon": "<emoji>", "title": "<title>", "description": "<1 sentence>"}
    ],
    "social_proof": "<testimonial or trust statement>",
    "cta_primary": "<primary CTA>",
    "cta_secondary": "<secondary CTA>"
  },
  "campaign_summary": {
    "strategy_rationale": "<2 sentences>",
    "key_message": "<single core message>",
    "urgency_hook": "<why act now>"
  }
}"""


def generate_campaign(segment_id: str, override_goals: dict = None) -> dict:
    start_ms = int(time.time() * 1000)
    brief    = build_unified_payload(segment_id, override_goals)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": build_system_prompt(brief)},
            {"role": "user",   "content": "Generate the campaign JSON: " + USER_PROMPT}
        ],
        temperature=0.75,
        max_tokens=2000,
        response_format={"type": "json_object"}
    )

    campaign_copy = json.loads(completion.choices[0].message.content)
    latency_ms    = int(time.time() * 1000) - start_ms

    return {
        "segment_id":    segment_id,
        "campaign_copy": campaign_copy,
        "model":         completion.model,
        "tokens_used":   completion.usage.total_tokens,
        "latency_ms":    latency_ms,
        "brief_snapshot": {
            "segment_name": brief["customer_segment"]["name"],
            "product_sku":  brief["products"][0]["sku"],
            "objective":    brief["campaign_goals"]["objective"],
            "channels":     brief["campaign_goals"]["channels"]
        }
    }
