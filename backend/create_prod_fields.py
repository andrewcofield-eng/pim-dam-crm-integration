import httpx
import asyncio

PROD_DIRECTUS     = "https://directus-production-9f53.up.railway.app"
DIRECTUS_EMAIL    = "admin@portfolio.com"
DIRECTUS_PASSWORD = "admin123"

AF_FIELDS = [
    {"field": "af_primary_use_case",           "type": "string"},
    {"field": "af_onboarding_fit",             "type": "string"},
    {"field": "af_event_fit",                  "type": "string"},
    {"field": "af_gifting_fit",                "type": "string"},
    {"field": "af_personalization_suitability","type": "string"},
    {"field": "af_value_tier",                 "type": "string"},
    {"field": "af_bundle_role",                "type": "string"},
    {"field": "af_recommended_cta_angle",      "type": "string"},
    {"field": "af_ideal_audience",             "type": "json"},
    {"field": "af_vertical_fit",               "type": "json"},
    {"field": "af_complementary_skus",         "type": "json"},
]

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{PROD_DIRECTUS}/auth/login",
            json={"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD})
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for f in AF_FIELDS:
            payload = {
                "field": f["field"],
                "type":  f["type"],
                "schema": {},
                "meta": {"hidden": False, "readonly": False}
            }
            r = await client.post(
                f"{PROD_DIRECTUS}/fields/products",
                headers=headers,
                json=payload,
                timeout=10
            )
            if r.status_code in [200, 204]:
                print(f"✅ Created: {f['field']}")
            elif r.status_code == 400 and "already exists" in r.text:
                print(f"⚠️  Exists:  {f['field']}")
            else:
                print(f"❌ Failed:  {f['field']} → {r.status_code}: {r.text[:80]}")

asyncio.run(main())