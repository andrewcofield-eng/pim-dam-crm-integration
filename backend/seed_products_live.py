"""
seed_products_live.py — Seed 18 products with real Cloudinary URLs
"""
import httpx
import asyncio
import os
from datetime import datetime

DIRECTUS_URL = "https://directus-production-9f53.up.railway.app"
DIRECTUS_EMAIL = "admin@portfolio.com"
DIRECTUS_PASSWORD = "admin123"

# 18 products with YOUR Cloudinary URLs
NEW_PRODUCTS = [
    {
        "sku": "TOP-003",
        "product_name": "Long Sleeve Henley",
        "short_description": "Classic cotton henley with three-button placket",
        "Description": "A versatile wardrobe staple in soft ring-spun cotton. Features a three-button placket, reinforced shoulder seams, and a modern athletic fit.",
        "category": "T-Shirts",
        "brand": "UrbanThread",
        "price": 39.99,
        "status": "active",
        "tags": ["henley", "long-sleeve", "cotton", "basics"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774234834/TOP-003_ehtxny.jpg",
        "cloudinary_public_id": "TOP-003_ehtxny",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "HOD-003",
        "product_name": "French Terry Hoodie",
        "short_description": "Midweight French terry with vintage wash",
        "Description": "Soft, looped French terry interior with a garment-washed exterior for that perfectly broken-in feel from day one.",
        "category": "Hoodies",
        "brand": "UrbanThread",
        "price": 72.99,
        "status": "active",
        "tags": ["hoodie", "french-terry", "vintage"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236178/HOD-003_vm9yux.jpg",
        "cloudinary_public_id": "HOD-003_vm9yux",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "HOD-004",
        "product_name": "Full-Zip Windbreaker Hoodie",
        "short_description": "Hybrid hoodie with water-resistant shell",
        "Description": "Best of both worlds: fleece comfort meets windbreaker protection. The bonded outer shell sheds light rain.",
        "category": "Hoodies",
        "brand": "UrbanThread",
        "price": 89.99,
        "status": "active",
        "tags": ["hoodie", "windbreaker", "hybrid", "outdoor"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236178/HOD-004_thzkod.jpg",
        "cloudinary_public_id": "HOD-004_thzkod",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "OUT-003",
        "product_name": "Insulated Vest",
        "short_description": "Lightweight insulated vest for layering",
        "Description": "The ultimate layering piece. Synthetic insulation provides warmth without bulk. Quilted pattern keeps fill evenly distributed.",
        "category": "Outerwear",
        "brand": "UrbanThread",
        "price": 84.99,
        "status": "active",
        "tags": ["vest", "insulated", "layering", "quilted"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236179/OUT-003_mrv2b1.jpg",
        "cloudinary_public_id": "OUT-003_mrv2b1",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "OUT-004",
        "product_name": "Wool Overcoat",
        "short_description": "Classic wool-blend overcoat",
        "Description": "Investment-piece quality at accessible price. Wool-poly blend resists wrinkles and water.",
        "category": "Outerwear",
        "brand": "UrbanThread",
        "price": 199.99,
        "status": "active",
        "tags": ["overcoat", "wool", "formal", "winter"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236179/OUT-004_yhklka.jpg",
        "cloudinary_public_id": "OUT-004_yhklka",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "DNM-004",
        "product_name": "Tapered Jogger",
        "short_description": "Elevated jogger with cuffed ankle",
        "Description": "Not your gym jogger. Premium cotton twill with a refined taper and subtle cuff.",
        "category": "Bottoms",
        "brand": "UrbanThread",
        "price": 64.99,
        "status": "active",
        "tags": ["jogger", "tapered", "casual", "twill"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236526/DNM-004_zfbmoo.jpg",
        "cloudinary_public_id": "DNM-004_zfbmoo",
        "target_segment": "Streetwear"
    },
    {
        "sku": "ACC-003",
        "product_name": "Canvas Belt",
        "short_description": "Durable canvas web belt with metal buckle",
        "Description": "Military-inspired web belt built to last. Heavy cotton canvas with antiqued brass buckle.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 29.99,
        "status": "active",
        "tags": ["belt", "canvas", "web-belt", "casual"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236169/ACC-003_ymymuu.jpg",
        "cloudinary_public_id": "ACC-003_ymymuu",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "ACC-004",
        "product_name": "Leather Weekender Bag",
        "short_description": "Full-grain leather weekend travel bag",
        "Description": "The only bag you need for 48-hour getaways. Full-grain leather develops a unique patina.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 249.99,
        "status": "active",
        "tags": ["bag", "leather", "weekender", "travel"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/ACC-004_kidq0y.jpg",
        "cloudinary_public_id": "ACC-004_kidq0y",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "ACC-005",
        "product_name": "Merino Wool Scarf",
        "short_description": "Ultra-soft merino wool scarf",
        "Description": "Fine-gauge merino wool that won't itch. Subtle ribbed texture adds visual interest.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 44.99,
        "status": "active",
        "tags": ["scarf", "merino", "wool", "winter"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236169/ACC-005_tsrzyb.jpg",
        "cloudinary_public_id": "ACC-005_tsrzyb",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "KNIT-001",
        "product_name": "Cable Knit Sweater",
        "short_description": "Traditional cable knit in cotton blend",
        "Description": "Heritage craftsmanship meets modern comfort. Classic cable pattern in a breathable cotton blend.",
        "category": "Sweaters",
        "brand": "UrbanThread",
        "price": 79.99,
        "status": "active",
        "tags": ["sweater", "cable-knit", "cotton", "classic"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/KNIT-001_yjajnw.jpg",
        "cloudinary_public_id": "KNIT-001_yjajnw",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "KNIT-002",
        "product_name": "Quarter-Zip Pullover",
        "short_description": "Lightweight quarter-zip for layering",
        "Description": "The perfect layering weight. Fine-gauge knit slides under jackets without bulk.",
        "category": "Sweaters",
        "brand": "UrbanThread",
        "price": 69.99,
        "status": "active",
        "tags": ["sweater", "quarter-zip", "layering", "lightweight"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/KNIT-002_ulqvek.jpg",
        "cloudinary_public_id": "KNIT-002_ulqvek",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "SHORT-001",
        "product_name": "Chino Short",
        "short_description": "Classic 9-inch inseam chino short",
        "Description": "The warm-weather equivalent of our bestselling chinos. Same stretch cotton blend.",
        "category": "Bottoms",
        "brand": "UrbanThread",
        "price": 49.99,
        "status": "active",
        "tags": ["shorts", "chino", "summer", "stretch"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236168/SHORT-001_n5cklw.jpg",
        "cloudinary_public_id": "SHORT-001_n5cklw",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "SHORT-002",
        "product_name": "Performance Athletic Short",
        "short_description": "Quick-dry athletic short with liner",
        "Description": "From morning run to coffee run. Lightweight shell with built-in compression liner.",
        "category": "Bottoms",
        "brand": "UrbanThread",
        "price": 44.99,
        "status": "active",
        "tags": ["shorts", "athletic", "performance", "quick-dry"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236526/SHORT-002_mjinid.jpg",
        "cloudinary_public_id": "SHORT-002_mjinid",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "SHIRT-001",
        "product_name": "Oxford Button-Down",
        "short_description": "Classic Oxford cloth button-down shirt",
        "Description": "The foundation of any smart wardrobe. Mid-weight Oxford cotton that improves with washing.",
        "category": "Shirts",
        "brand": "UrbanThread",
        "price": 59.99,
        "status": "active",
        "tags": ["shirt", "oxford", "button-down", "classic"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/SHIRT-001_ghcvts.jpg",
        "cloudinary_public_id": "SHIRT-001_ghcvts",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "SHIRT-002",
        "product_name": "Flannel Work Shirt",
        "short_description": "Heavyweight flannel in traditional patterns",
        "Description": "Built for the workshop and the weekend. Double-brushed cotton flannel for exceptional softness.",
        "category": "Shirts",
        "brand": "UrbanThread",
        "price": 64.99,
        "status": "active",
        "tags": ["shirt", "flannel", "workwear", "heavyweight"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/SHIRT-002_suuyfo.jpg",
        "cloudinary_public_id": "SHIRT-002_suuyfo",
        "target_segment": "Streetwear"
    },
    {
        "sku": "SWIM-001",
        "product_name": "Swim Trunk",
        "short_description": "Quick-dry swim trunk with liner",
        "Description": "Vacation-ready from day one. Lightweight shell dries fast. Built-in mesh liner for support.",
        "category": "Swim",
        "brand": "UrbanThread",
        "price": 54.99,
        "status": "active",
        "tags": ["swim", "trunks", "quick-dry", "summer"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236527/SWIM-001_hoqsjv.jpg",
        "cloudinary_public_id": "SWIM-001_hoqsjv",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "SOCK-001",
        "product_name": "Merino Wool Dress Sock",
        "short_description": "Ultra-soft merino dress socks, 3-pack",
        "Description": "Upgrade your sock drawer. Fine merino wool regulates temperature and resists odor.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 34.99,
        "status": "active",
        "tags": ["socks", "merino", "wool", "dress"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/SOCK-001_wghtxb.jpg",
        "cloudinary_public_id": "SOCK-001_wghtxb",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "UNDER-001",
        "product_name": "Modal Blend Boxer Brief",
        "short_description": "Silky modal blend boxer brief, 3-pack",
        "Description": "The first layer matters. Silky modal blend feels cool against skin. No-ride leg design.",
        "category": "Basics",
        "brand": "UrbanThread",
        "price": 39.99,
        "status": "active",
        "tags": ["underwear", "modal", "boxer-brief", "basics"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1774236170/UNDER-001_rx940w.jpg",
        "cloudinary_public_id": "UNDER-001_rx940w",
        "target_segment": "Everyday Basics"
    }
]

# NOTE: Missing from your upload - need these two:
# TOP-004 - Performance Polo
# DNM-003 - Chino Pants (straight fit)

async def get_directus_token():
    """Authenticate with Directus"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DIRECTUS_URL}/auth/login",
            json={"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD}
        )
        return response.json()["data"]["access_token"]

async def seed_products():
    """Import all products to Directus"""
    token = await get_directus_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        created = 0
        skipped = 0
        
        for product in NEW_PRODUCTS:
            # Check if product already exists
            try:
                check = await client.get(
                    f"{DIRECTUS_URL}/items/products?filter[sku][_eq]={product['sku']}",
                    headers=headers
                )
                existing = check.json().get("data", [])
                if existing:
                    print(f"⏭️  Skipped (exists): {product['sku']}")
                    skipped += 1
                    continue
            except:
                pass
            
            # Create new product
            try:
                response = await client.post(
                    f"{DIRECTUS_URL}/items/products",
                    headers=headers,
                    json=product
                )
                if response.status_code in [200, 201]:
                    print(f"✅ Created: {product['sku']} - {product['product_name']}")
                    created += 1
                else:
                    print(f"⚠️  Failed {product['sku']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error {product['sku']}: {str(e)}")
        
        print(f"\n🎉 Done! Created {created}, Skipped {skipped}, Total {created + skipped}/18")

if __name__ == "__main__":
    print("🚀 Seeding 18 products to Directus with Cloudinary images...")
    print("⚠️  NOTE: TOP-004 and DNM-003 are missing from Cloudinary - upload those too!\n")
    asyncio.run(seed_products())