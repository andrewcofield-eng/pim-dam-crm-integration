import httpx
import asyncio

# ── Config ────────────────────────────────────────────────
LOCAL_API    = "http://localhost:8000"
PROD_DIRECTUS = "https://directus-production-9f53.up.railway.app"
DIRECTUS_EMAIL    = "admin@portfolio.com"
DIRECTUS_PASSWORD = "admin123"

# ── Get production Directus token ─────────────────────────
async def get_prod_token():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{PROD_DIRECTUS}/auth/login",
            json={"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD})
        return r.json()["data"]["access_token"]

# ── Main migration ────────────────────────────────────────
async def migrate():
    print("Step 1: Fetching enriched products from local...")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{LOCAL_API}/products/export", timeout=30)
        local_data = r.json()

    products = local_data.get("products", [])
    print(f"  Found {len(products)} enriched products locally")

    if not products:
        print("ERROR: No local products found. Is your local server running?")
        return

    print("Step 2: Getting production Directus token...")
    token = await get_prod_token()
    headers = {"Authorization": f"Bearer {token}"}

    print("Step 3: Fetching production product IDs...")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PROD_DIRECTUS}/items/products?limit=100", headers=headers)
        prod_products = r.json().get("data", [])

    # Build SKU -> ID map for production
    sku_to_id = {p["sku"]: p["id"] for p in prod_products if p.get("sku")}
    print(f"  Found {len(sku_to_id)} products in production Directus")

    print("Step 4: Patching af_* fields into production...")
    success = 0
    failed  = 0

    async with httpx.AsyncClient() as client:
        for p in products:
            sku = p.get("sku")
            prod_id = sku_to_id.get(sku)
            if not prod_id:
                print(f"  SKIP: {sku} not found in production")
                failed += 1
                continue

            patch = {
                "af_primary_use_case":          p.get("marketing_fit", {}).get("primary_use_case"),
                "af_ideal_audience":            p.get("marketing_fit", {}).get("ideal_audience", []),
                "af_vertical_fit":              p.get("marketing_fit", {}).get("vertical_fit", []),
                "af_onboarding_fit":            p.get("scenario_scores", {}).get("onboarding"),
                "af_event_fit":                 p.get("scenario_scores", {}).get("events"),
                "af_gifting_fit":               p.get("scenario_scores", {}).get("gifting"),
                "af_personalization_suitability": p.get("merchandising", {}).get("personalization_suitability"),
                "af_value_tier":                p.get("merchandising", {}).get("value_tier"),
                "af_bundle_role":               p.get("merchandising", {}).get("bundle_role"),
                "af_complementary_skus":        p.get("merchandising", {}).get("complementary_skus", []),
                "af_recommended_cta_angle":     p.get("messaging", {}).get("recommended_cta"),
            }

            r = await client.patch(
                f"{PROD_DIRECTUS}/items/products/{prod_id}",
                headers=headers,
                json=patch,
                timeout=10
            )
            if r.status_code in [200, 204]:
                print(f"  ✅ {sku}")
                success += 1
            else:
                print(f"  ❌ {sku}: {r.status_code} {r.text[:80]}")
                failed += 1

    print(f"\nDone! {success} patched, {failed} failed.")

asyncio.run(migrate())