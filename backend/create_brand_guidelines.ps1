$directusUrl = "https://directus-production-9f53.up.railway.app"

$auth = Invoke-RestMethod -Uri "$directusUrl/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"admin@portfolio.com","password":"admin123"}'
$token = $auth.data.access_token
$headers = @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
Write-Host "Authenticated OK"

$body = @{
    collection = "brand_guidelines"
    meta = @{ icon = "style"; note = "Brand voice and guidelines for AI campaign generation" }
    schema = @{ name = "brand_guidelines" }
    fields = @(
        @{ field = "id"; type = "integer"; meta = @{ hidden = $true; readonly = $true }; schema = @{ is_primary_key = $true; has_auto_increment = $true } }
        @{ field = "brand_name"; type = "string"; meta = @{ width = "half" }; schema = @{} }
        @{ field = "tagline"; type = "string"; meta = @{ width = "half" }; schema = @{} }
        @{ field = "voice_tone"; type = "string"; meta = @{ width = "full" }; schema = @{} }
        @{ field = "brand_promise"; type = "text"; meta = @{ width = "full"; interface = "input-multiline" }; schema = @{} }
        @{ field = "key_messages"; type = "text"; meta = @{ width = "full" }; schema = @{} }
        @{ field = "words_to_use"; type = "text"; meta = @{ width = "half" }; schema = @{} }
        @{ field = "words_to_avoid"; type = "text"; meta = @{ width = "half" }; schema = @{} }
        @{ field = "primary_color"; type = "string"; meta = @{ width = "half" }; schema = @{} }
        @{ field = "secondary_color"; type = "string"; meta = @{ width = "half" }; schema = @{} }
        @{ field = "logo_cloudinary_url"; type = "string"; meta = @{ width = "full" }; schema = @{} }
        @{ field = "target_industries"; type = "text"; meta = @{ width = "full" }; schema = @{} }
        @{ field = "compliance_notes"; type = "text"; meta = @{ width = "full" }; schema = @{} }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "$directusUrl/collections" -Method POST -Headers $headers -Body $body
Write-Host "Collection created!"

$brandData = '{"brand_name":"UrbanThread","tagline":"Gear Built for the Journey","voice_tone":"Bold, Inspiring, Performance-driven, Authentic","brand_promise":"We equip B2B buyers with high-performance branded apparel and gear that their teams are proud to wear.","key_messages":"Sustainable materials, Technical performance, Custom branding at scale, Fast turnaround, Bulk pricing","words_to_use":"performance, sustainable, custom, durable, gear, team, journey, built, authentic, quality","words_to_avoid":"cheap, basic, generic, discount, just, simply, easy","primary_color":"#2D6A4F","secondary_color":"#F4A261","logo_cloudinary_url":"","target_industries":"Outdoor Apparel Retail, Fitness Chain, Corporate Merchandise, Adventure Travel, Event Management","compliance_notes":"Do not make specific durability claims without product testing data."}'

Invoke-RestMethod -Uri "$directusUrl/items/brand_guidelines" -Method POST -Headers $headers -Body $brandData
Write-Host "Brand data seeded!"
