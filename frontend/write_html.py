f = open('index.html', 'w', encoding='utf-8')
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agenic Flow ABM Dashboard</title>
<link rel="stylesheet" href="dashboard.css">
</head>
<body>
<header><div class="header-inner"><div class="logo"><span class="logo-main">Agenic Flow</span></div></div></header>
<main>
<section class="panel"><div class="panel-header"><h2>Prospects</h2><button onclick="loadProspects()">Refresh</button></div><div id="prospectsMeta"></div><div id="prospectsList"></div></section>
<section class="panel"><div class="panel-header"><h2>Campaign</h2></div><div id="campaignPlaceholder"><p>Select prospect</p></div><div id="campaignOutput" style="display:none"><div id="campaignAccount"></div><div id="campaignText" style="max-height:400px;overflow-y:auto"></div></div></section>
</main>
<section><div class="panel-header"><h2>Products</h2></div><div id="productGrid" class="product-grid"></div></section>
<footer><p>Agenic Flow Marketing</p></footer>
<script>
var API = "https://pim-dam-crm-integration-production.up.railway.app";
var token = null;

function getToken() {
    return fetch(API + "/auth/token").then(r => r.json()).then(d => {
        token = d.token;
        return token;
    });
}

function loadProspects() {
    if (!token) return;
    var url = API + "/abm/warm-prospects?directus_url=https://directus-production-9f53.up.railway.app&directus_token=" + token;
    fetch(url).then(r => r.json()).then(d => {
        document.getElementById("prospectsMeta").textContent = d.warm_prospects_count + " prospects";
        var list = document.getElementById("prospectsList");
        list.innerHTML = "";
        d.prospects.forEach(function(p, i) {
            var card = document.createElement("div");
            card.className = "prospect-card";
            card.textContent = p.company_name + " (" + p.engagement_score + ")";
            card.onclick = function() { selectProspect(p); };
            list.appendChild(card);
        });
    });
}

function selectProspect(p) {
    document.getElementById("campaignPlaceholder").style.display = "none";
    document.getElementById("campaignOutput").style.display = "block";
    document.getElementById("campaignAccount").textContent = p.company_name;
    document.getElementById("campaignText").textContent = "Loading...";
    
    var url = API + "/abm/campaign/generate?account_id=" + p.account_id + "&directus_url=https://directus-production-9f53.up.railway.app&directus_token=" + token;
    
    fetch(url, {method: "POST"}).then(r => r.json()).then(d => {
        document.getElementById("campaignText").textContent = d.campaign;
    }).catch(e => {
        document.getElementById("campaignText").textContent = "Error: " + e;
    });
}

function loadProducts() {
    fetch(API + "/products").then(r => r.json()).then(data => {
        var products = data.value || data;
        var grid = document.getElementById("productGrid");
        grid.innerHTML = "";
        products.forEach(p => {
            var card = document.createElement("div");
            card.className = "product-card";
            card.style.padding = "12px";
            card.style.border = "1px solid #ddd";
            card.style.borderRadius = "8px";
            card.style.backgroundColor = "#f9f9f9";
            
            var img = document.createElement("img");
            img.src = p.cloudinary_url || "https://via.placeholder.com/200";
            img.alt = p.product_name;
            img.style.width = "100%";
            img.style.height = "200px";
            img.style.objectFit = "cover";
            img.style.borderRadius = "6px";
            img.style.marginBottom = "10px";
            
            var sku = document.createElement("div");
            sku.style.fontSize = "0.75rem";
            sku.style.color = "#999";
            sku.style.marginBottom = "4px";
            sku.textContent = p.sku;
            
            var name = document.createElement("div");
            name.style.fontWeight = "600";
            name.style.fontSize = "0.95rem";
            name.style.marginBottom = "4px";
            name.textContent = p.product_name;
            
            var short = document.createElement("div");
            short.style.fontSize = "0.8rem";
            short.style.color = "#666";
            short.style.marginBottom = "6px";
            short.textContent = p.short_description;
            
            var desc = document.createElement("div");
            desc.style.fontSize = "0.75rem";
            desc.style.color = "#888";
            desc.style.lineHeight = "1.3";
            desc.style.marginBottom = "8px";
            desc.textContent = p.Description;
            
            var price = document.createElement("div");
            price.style.fontWeight = "700";
            price.style.fontSize = "0.95rem";
            price.style.color = "#005280";
            price.textContent = "$" + parseFloat(p.price).toFixed(2);
            
            card.appendChild(img);
            card.appendChild(sku);
            card.appendChild(name);
            card.appendChild(short);
            card.appendChild(desc);
            card.appendChild(price);
            grid.appendChild(card);
        });
    });
}

getToken().then(() => {
    loadProspects();
    loadProducts();
});
</script>
</body>
</html>'''
f.write(html)
f.close()
print("Updated with images and descriptions")
