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
<header>
<div class="header-inner">
<div class="logo">
<span class="logo-main">Agenic Flow</span>
<span class="logo-sub">ABM Intelligence Dashboard</span>
</div>
<div class="header-status">
<span class="status-dot" id="statusDot"></span>
<span id="statusText">Connecting...</span>
</div>
</div>
</header>
<main>
<section class="panel" id="prospectsPanel">
<div class="panel-header">
<h2>Warm Prospects</h2>
<button class="btn-refresh" onclick="loadProspects()">Refresh</button>
</div>
<div class="panel-meta" id="prospectsMeta">Loading...</div>
<div id="prospectsList" class="prospects-list"></div>
</section>
<section class="panel" id="campaignPanel">
<div class="panel-header">
<h2>ABM Campaign Generator</h2>
<span id="campaignStatus" class="campaign-status"></span>
</div>
<div id="campaignPlaceholder" class="campaign-placeholder">
<p>Select a prospect to generate a personalized ABM campaign</p>
</div>
<div id="campaignOutput" class="campaign-output" style="display:none;">
<div class="campaign-account" id="campaignAccount"></div>
<div class="campaign-text" id="campaignText"></div>
</div>
</section>
</main>
<section class="products-section">
<div class="panel-header">
<h2>UrbanThread Product Catalog</h2>
<span id="productCount" class="badge"></span>
</div>
<div id="productGrid" class="product-grid"></div>
</section>
<footer>
<p>Agenic Flow Marketing - Autonomous ABM powered by PIM + AI</p>
</footer>
<script>
var API = "https://pim-dam-crm-integration-production.up.railway.app";
var directusToken = null;

function setStatus(online) {
    document.getElementById("statusDot").className = online ? "status-dot online" : "status-dot offline";
    document.getElementById("statusText").textContent = online ? "System Online" : "Connection Error";
}

function getDirectusToken() {
    return fetch(API + "/auth/token")
    .then(r => r.json())
    .then(d => { directusToken = d.token; setStatus(true); })
    .catch(e => setStatus(false));
}

function loadProspects() {
    document.getElementById("prospectsMeta").textContent = "Loading...";
    fetch(API + "/abm/warm-prospects?directus_url=https://directus-production-9f53.up.railway.app&directus_token=" + directusToken)
    .then(r => r.json())
    .then(d => {
        document.getElementById("prospectsMeta").innerHTML = "<strong>" + d.warm_prospects_count + " warm prospects</strong>";
        var list = document.getElementById("prospectsList");
        d.prospects.forEach((p, i) => {
            var card = document.createElement("div");
            card.className = i === 0 ? "prospect-card hottest" : "prospect-card";
            card.onclick = () => selectProspect(p);
            var html = "<div class='prospect-rank'>#" + (i+1) + "</div>";
            html += "<div class='prospect-info'>";
            html += "<div class='prospect-name'>" + p.company_name + "</div>";
            html += "<div class='prospect-meta'>" + p.industry + " - " + p.buying_stage + "</div>";
            html += "<div class='prospect-contact'>" + p.contact.name + " - " + p.contact.title + "</div>";
            html += "</div>";
            html += "<div class='prospect-score'><div class='score-number'>" + p.engagement_score + "</div><div class='score-label'>pts</div></div>";
            card.innerHTML = html;
            list.appendChild(card);
        });
    })
    .catch(e => console.error("Error:", e));
}

function selectProspect(p) {
    document.getElementById("campaignPlaceholder").style.display = "none";
    document.getElementById("campaignOutput").style.display = "block";
    document.getElementById("campaignAccount").innerHTML = "<strong>" + p.company_name + "</strong> - " + p.industry;
    document.getElementById("campaignStatus").textContent = "Generating...";
    generateCampaign(p.account_id);
}

function generateCampaign(accountId) {
    fetch(API + "/abm/campaign/generate?account_id=" + accountId + "&directus_url=https://directus-production-9f53.up.railway.app&directus_token=" + directusToken, {method:"POST"})
    .then(r => r.json())
    .then(d => {
        document.getElementById("campaignText").innerHTML = "<p>" + d.campaign.replace(/\n/g, "</p><p>") + "</p>";
        document.getElementById("campaignStatus").textContent = "Ready";
    })
    .catch(e => console.error("Campaign error:", e));
}

function loadProducts() {
    fetch(API + "/products")
    .then(r => r.json())
    .then(p => {
        document.getElementById("productCount").textContent = p.length + " products";
        var grid = document.getElementById("productGrid");
        p.forEach(prod => {
            var card = document.createElement("div");
            card.className = "product-card";
            card.innerHTML = "<div class='product-sku'>" + prod.sku + "</div><div class='product-name'>" + prod.product_name + "</div><div class='product-category'>" + prod.category + "</div><div class='product-price'>$" + parseFloat(prod.price).toFixed(2) + "</div>";
            grid.appendChild(card);
        });
    });
}

getDirectusToken().then(() => { loadProspects(); loadProducts(); });
</script>
</body>
</html>'''
f.write(html)
f.close()
print("HTML written successfully")
