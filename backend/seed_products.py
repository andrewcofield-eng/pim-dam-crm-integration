"""
seed_products.py — Bulk import 20 products to Directus with Cloudinary images
"""
import httpx
import asyncio
import os
from datetime import datetime

DIRECTUS_URL = "https://directus-production-9f53.up.railway.app"
DIRECTUS_EMAIL = "admin@portfolio.com"
DIRECTUS_PASSWORD = "admin123"

# 20 new UrbanThread products with Cloudinary image URLs
NEW_PRODUCTS = [
    {
        "sku": "TOP-003",
        "product_name": "Long Sleeve Henley",
        "short_description": "Classic cotton henley with three-button placket",
        "Description": "A versatile wardrobe staple in soft ring-spun cotton. Features a three-button placket, reinforced shoulder seams, and a modern athletic fit that works tucked or untucked.",
        "category": "T-Shirts",
        "brand": "UrbanThread",
        "price": 39.99,
        "status": "active",
        "tags": ["henley", "long-sleeve", "cotton", "basics"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692801/henley-longsleeve.png",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "TOP-004",
        "product_name": "Performance Polo",
        "short_description": "Moisture-wicking polo for active professionals",
        "Description": "Built for the commute and the conference room. Technical fabric moves with you, resists wrinkles, and keeps you cool. Subtle texture elevates it above basic polos.",
        "category": "T-Shirts",
        "brand": "UrbanThread",
        "price": 54.99,
        "status": "active",
        "tags": ["polo", "performance", "workwear"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692802/performance-polo.png",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "HOD-003",
        "product_name": "French Terry Hoodie",
        "short_description": "Midweight French terry with vintage wash",
        "Description": "Soft, looped French terry interior with a garment-washed exterior for that perfectly broken-in feel from day one. Raglan sleeves allow full range of motion.",
        "category": "Hoodies",
        "brand": "UrbanThread",
        "price": 72.99,
        "status": "active",
        "tags": ["hoodie", "french-terry", "vintage"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692803/french-terry-hoodie.png",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "HOD-004",
        "product_name": "Full-Zip Windbreaker Hoodie",
        "short_description": "Hybrid hoodie with water-resistant shell",
        "Description": "Best of both worlds: fleece comfort meets windbreaker protection. The bonded outer shell sheds light rain while the brushed interior keeps you warm on breezy days.",
        "category": "Hoodies",
        "brand": "UrbanThread",
        "price": 89.99,
        "status": "active",
        "tags": ["hoodie", "windbreaker", "hybrid", "outdoor"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692804/windbreaker-hoodie.png",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "DNM-003",
        "product_name": "Straight Fit Chino",
        "short_description": "Stretch chino in classic straight fit",
        "Description": "The weekday warrior. Stretch cotton blend moves with you through commutes, meetings, and after-work drinks. Straight fit works with any shoe style from sneakers to boots.",
        "category": "Bottoms",
        "brand": "UrbanThread",
        "price": 69.99,
        "status": "active",
        "tags": ["chino", "stretch", "workwear", "straight-fit"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692805/chino-straight.png",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "DNM-004",
        "product_name": "Tapered Jogger",
        "short_description": "Elevated jogger with cuffed ankle",
        "Description": "Not your gym jogger. Premium cotton twill with a refined taper and subtle cuff. Elastic waist with external drawcord for adjustability. Dress it up or down.",
        "category": "Bottoms",
        "brand": "UrbanThread",
        "price": 64.99,
        "status": "active",
        "tags": ["jogger", "tapered", "casual", "twill"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692806/tapered-jogger.png",
        "target_segment": "Streetwear"
    },
    {
        "sku": "OUT-003",
        "product_name": "Insulated Vest",
        "short_description": "Lightweight insulated vest for layering",
        "Description": "The ultimate layering piece. Synthetic insulation provides warmth without bulk. Quilted pattern keeps fill evenly distributed. Stand collar protects against wind.",
        "category": "Outerwear",
        "brand": "UrbanThread",
        "price": 84.99,
        "status": "active",
        "tags": ["vest", "insulated", "layering", "quilted"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692807/insulated-vest.png",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "OUT-004",
        "product_name": "Wool Overcoat",
        "short_description": "Classic wool-blend overcoat",
        "Description": "Investment-piece quality at accessible price. Wool-poly blend resists wrinkles and water. Full lining glides over layers. Notch lapels and welt pockets keep it timeless.",
        "category": "Outerwear",
        "brand": "UrbanThread",
        "price": 199.99,
        "status": "active",
        "tags": ["overcoat", "wool", "formal", "winter"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692808/wool-overcoat.png",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "ACC-003",
        "product_name": "Canvas Belt",
        "short_description": "Durable canvas web belt with metal buckle",
        "Description": "Military-inspired web belt built to last. Heavy cotton canvas with antiqued brass buckle. Cut-to-fit design means one size truly fits all. Ages beautifully with wear.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 29.99,
        "status": "active",
        "tags": ["belt", "canvas", "web-belt", "casual"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692809/canvas-belt.png",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "ACC-004",
        "product_name": "Leather Weekender Bag",
        "short_description": "Full-grain leather weekend travel bag",
        "Description": "The only bag you need for 48-hour getaways. Full-grain leather develops a unique patina. Reinforced handles and removable shoulder strap. Interior pockets keep essentials organized.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 249.99,
        "status": "active",
        "tags": ["bag", "leather", "weekender", "travel"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692810/leather-weekender.png",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "ACC-005",
        "product_name": "Merino Wool Scarf",
        "short_description": "Ultra-soft merino wool scarf",
        "Description": "Fine-gauge merino wool that won't itch. Subtle ribbed texture adds visual interest. Generous length allows multiple wrapping styles. Naturally temperature-regulating.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 44.99,
        "status": "active",
        "tags": ["scarf", "merino", "wool", "winter"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692811/merino-scarf.png",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "KNIT-001",
        "product_name": "Cable Knit Sweater",
        "short_description": "Traditional cable knit in cotton blend",
        "Description": "Heritage craftsmanship meets modern comfort. Classic cable pattern in a breathable cotton blend. Ribbed cuffs and hem hold their shape. Crew neck layers perfectly over collared shirts.",
        "category": "Sweaters",
        "brand": "UrbanThread",
        "price": 79.99,
        "status": "active",
        "tags": ["sweater", "cable-knit", "cotton", "classic"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692812/cable-knit.png",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "KNIT-002",
        "product_name": "Quarter-Zip Pullover",
        "short_description": "Lightweight quarter-zip for layering",
        "Description": "The perfect layering weight. Fine-gauge knit slides under jackets without bulk. Quarter-zip allows temperature regulation. Clean lines work in casual or business-casual settings.",
        "category": "Sweaters",
        "brand": "UrbanThread",
        "price": 69.99,
        "status": "active",
        "tags": ["sweater", "quarter-zip", "layering", "lightweight"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692813/quarter-zip.png",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "SHORT-001",
        "product_name": "Chino Short",
        "short_description": "Classic 9-inch inseam chino short",
        "Description": "The warm-weather equivalent of our bestselling chinos. Same stretch cotton blend. 9-inch inseam hits above the knee for modern proportion. Garment-washed for softness.",
        "category": "Bottoms",
        "brand": "UrbanThread",
        "price": 49.99,
        "status": "active",
        "tags": ["shorts", "chino", "summer", "stretch"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692814/chino-short.png",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "SHORT-002",
        "product_name": "Performance Athletic Short",
        "short_description": "Quick-dry athletic short with liner",
        "Description": "From morning run to coffee run. Lightweight shell with built-in compression liner. Zippered back pocket secures keys and cards. Reflective details for low-light visibility.",
        "category": "Bottoms",
        "brand": "UrbanThread",
        "price": 44.99,
        "status": "active",
        "tags": ["shorts", "athletic", "performance", "quick-dry"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692815/athletic-short.png",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "SHIRT-001",
        "product_name": "Oxford Button-Down",
        "short_description": "Classic Oxford cloth button-down shirt",
        "Description": "The foundation of any smart wardrobe. Mid-weight Oxford cotton that improves with washing. Button-down collar stays put under sweaters and blazers. Slightly relaxed fit for all-day comfort.",
        "category": "Shirts",
        "brand": "UrbanThread",
        "price": 59.99,
        "status": "active",
        "tags": ["shirt", "oxford", "button-down", "classic"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692816/oxford-shirt.png",
        "target_segment": "Everyday Basics"
    },
    {
        "sku": "SHIRT-002",
        "product_name": "Flannel Work Shirt",
        "short_description": "Heavyweight flannel in traditional patterns",
        "Description": "Built for the workshop and the weekend. Double-brushed cotton flannel for exceptional softness. Two chest pockets with flaps. Reinforced elbows stand up to real work.",
        "category": "Shirts",
        "brand": "UrbanThread",
        "price": 64.99,
        "status": "active",
        "tags": ["shirt", "flannel", "workwear", "heavyweight"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692817/flannel-shirt.png",
        "target_segment": "Streetwear"
    },
    {
        "sku": "SWIM-001",
        "product_name": "Swim Trunk",
        "short_description": "Quick-dry swim trunk with liner",
        "Description": "Vacation-ready from day one. Lightweight shell dries fast. Built-in mesh liner for support. Zippered back pocket keeps valuables secure. 7-inch inseam for modern proportion.",
        "category": "Swim",
        "brand": "UrbanThread",
        "price": 54.99,
        "status": "active",
        "tags": ["swim", "trunks", "quick-dry", "summer"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692818/swim-trunk.png",
        "target_segment": "Active Lifestyle"
    },
    {
        "sku": "SOCK-001",
        "product_name": "Merino Wool Dress Sock",
        "short_description": "Ultra-soft merino dress socks, 3-pack",
        "Description": "Upgrade your sock drawer. Fine merino wool regulates temperature and resists odor. Reinforced heel and toe for durability. Subtle ribbing adds texture. Three neutral colors in each pack.",
        "category": "Accessories",
        "brand": "UrbanThread",
        "price": 34.99,
        "status": "active",
        "tags": ["socks", "merino", "wool", "dress"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692819/merino-socks.png",
        "target_segment": "Premium Casual"
    },
    {
        "sku": "UNDER-001",
        "product_name": "Modal Blend Boxer Brief",
        "short_description": "Silky modal blend boxer brief, 3-pack",
        "Description": "The first layer matters. Silky modal blend feels cool against skin. No-ride leg design stays put all day. Contoured pouch provides support without compression. Three-pack in assorted colors.",
        "category": "Basics",
        "brand": "UrbanThread",
        "price": 39.99,
        "status": "active",
        "tags": ["underwear", "modal", "boxer-brief", "basics"],
        "cloudinary_url": "https://res.cloudinary.com/dp0cdq8bj/image/upload/v1742692820/boxer-brief.png",
        "target_segment": "Everyday Basics"
    }
]

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
        for product in NEW_PRODUCTS:
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
                    print(f"⚠️  Failed {product['sku']}: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Error {product['sku']}: {str(e)}")
        
        print(f"\n🎉 Done! Created {created}/{len(NEW_PRODUCTS)} products")

if __name__ == "__main__":
    print("🚀 Seeding 20 products to Directus...")
    asyncio.run(seed_products())