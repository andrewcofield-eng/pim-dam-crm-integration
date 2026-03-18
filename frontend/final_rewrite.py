f = open("index.html","w",encoding="utf-8")
f.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agenic Flow ABM Dashboard</title>
<link rel="stylesheet" href="dashboard.css">
</head>
<body>
<header><div class="header-inner"><div class="logo"><span class="logo-main">Agenic Flow</span></div><div class="header-status"><div class="status-dot" id="statusDot"></div><span id="statusText" style="font-size:0.82rem;color:var(--text-secondary);">Connecting...</span></div></div></header>
<main>
<section class="panel"><div class="panel-header"><h2>Prospects</h2><button class="btn-refresh" onclick="loadProspects()">Refresh</button></div><div id="prospectsMeta" class="panel-meta"></div><div id="prospectsList" class="prospects-list"></div></section>
<section class="panel"><div class="panel-header"><h2>ABM Campaign</h2></div><div id="campaignPlaceholder" class="campaign-placeholder"><p>Select a prospect</p></div><div id="campaignOutput" style="display:none"><div id="campaignAccount" class="campaign-account"></div><div id="campaignText" class="campaign-text"></div></div></section>
</main>
<section class="products-section"><div class="panel-header"><h2>AI Campaign Generator</h2><span class="badge">Segment-Aware</span></div><div class="panel" style="max-width:100%"><div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;margin-bottom:1.25rem;"><label for="segmentSelect" style="font-size:0.9rem;color:var(--text-secondary);">Segment:</label><select id="segmentSelect" class="seg-select"><option value="seg_001">seg_001 - High-Value Repeat Buyers</option><option value="seg_002">seg_002 - At-Risk Subscribers</option><option value="seg_003">seg_003 - New Customer Acquisition</option></select><button class="btn-refresh" id="generateBtn" onclick="generateAICampaign()">Generate Campaign</button><span id="aiCampaignStatus" style="font-size:0.82rem;color:var(--text-secondary);"></span></div><div id="aiCampaignPlaceholder" style="color:var(--text-secondary);font-size:0.9rem;padding:1rem 0;">Select a segment and click Generate.</div><div id="aiCampaignOutput" style="display:none"><div class="ai-campaign-grid"><div class="ai-block"><h4>Email Copy</h4><p id="aiEmail"></p></div><div class="ai-block"><h4>Ad Headlines</h4><ul id="aiHeadlines"></ul></div><div class="ai-block"><h4>Landing Page Copy</h4><p id="aiLanding"></p></div></div><div class="ai-block" style="margin-top:1rem"><h4>Campaign Summary</h4><p id="aiSummary"></p></div></div></div></section>
<section class="products-section" style="margin-top:0"><div class="panel-header"><h2>Shopify Metrics</h2><button class="btn-refresh" onclick="loadShopifyChart()">Refresh</button></div><div class="panel" style="max-width:100%"><canvas id="shopifyChart" height="80"></canvas><div id="shopifyStatus" style="font-size:0.82rem;color:var(--text-secondary);margin-top:0.75rem;"></div></div></section>
<section class="products-section" style="margin-top:0"><div class="panel-header"><h2>Products</h2><span id="productCount" class="badge"></span></div><div id="productGrid" class="product-grid"></div></section>
<footer><p>Agenic Flow Marketing</p></footer>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script>
var API = 'https://pim-dam-crm-integration-production.up.railway.app';
var token = null;
var shopifyChart = null;

function setStatus(online) {
  document.getElementById('statusDot').className = 'status-dot ' + (online ? 'online' : 'offline');
  document.getElementById('statusText').textContent = online ? 'Connected' : 'Offline';
}

function getToken() {
  return fetch(API + '/auth/token')
    .then(function(r) { return r.json(); })
    .then(function(d) { token = d.token; setStatus(true); return token; })
    .catch(function(e) { setStatus(false); });
}

function loadProspects() {
  if (!token) return;
  fetch(API + '/abm/warm-prospects?directus_url=https://directus-production-9f53.up.railway.app&directus_token=' + token)
    .then(function(r) { return r.json(); })
    .then(function(d) {
      document.getElementById('prospectsMeta').textContent = (d.warm_prospects_count || 0) + ' warm prospects';
      var list = document.getElementById('prospectsList');
      list.innerHTML = '';
      (d.prospects || []).forEach(function(p, i) {
        var card = document.createElement('div');
        card.className = 'prospect-card' + (i === 0 ? ' hottest' : '');
        var rank = document.createElement('div'); rank.className = 'prospect-rank'; rank.textContent = '#' + (i+1);
        var info = document.createElement('div'); info.className = 'prospect-info';
        var nm = document.createElement('div'); nm.className = 'prospect-name'; nm.textContent = p.company_name || '';
        var mt = document.createElement('div'); mt.className = 'prospect-meta'; mt.textContent = p.account_value || '';
        var ct = document.createElement('div'); ct.className = 'prospect-contact';
        ct.textContent = (p.contact_id && p.contact_id !== 'None') ? 'Contact: ' + p.contact_id : 'No contact linked';
        info.appendChild(nm); info.appendChild(mt); info.appendChild(ct);
        var sb = document.createElement('div'); sb.className = 'prospect-score';
        var sn = document.createElement('div'); sn.className = 'score-number'; sn.textContent = p.engagement_score || '--';
        var sl = document.createElement('div'); sl.className = 'score-label'; sl.textContent = 'Score';
        sb.appendChild(sn); sb.appendChild(sl);
        card.appendChild(rank); card.appendChild(info); card.appendChild(sb);
        card.onclick = function() { selectProspect(p); };
        list.appendChild(card);
      });
    })
    .catch(function(e) { document.getElementById('prospectsMeta').textContent = 'Error: ' + e.message; });
}

function selectProspect(p) {
  document.getElementById('campaignPlaceholder').style.display = 'none';
  document.getElementById('campaignOutput').style.display = 'block';
  document.getElementById('campaignAccount').textContent = p.company_name;
  document.getElementById('campaignText').innerHTML = '<div class=generating>Generating...</div>';
  fetch(API + '/abm/campaign/generate?account_id=' + p.account_id + '&directus_url=https://directus-production-9f53.up.railway.app&directus_token=' + token, {method:'POST'})
    .then(function(r) { return r.json(); })
    .then(function(d) { document.getElementById('campaignText').textContent = d.campaign || JSON.stringify(d); })
    .catch(function(e) { document.getElementById('campaignText').textContent = 'Error: ' + e; });
}

function generateAICampaign() {
  var seg = document.getElementById('segmentSelect').value;
  var btn = document.getElementById('generateBtn');
  var status = document.getElementById('aiCampaignStatus');
  var output = document.getElementById('aiCampaignOutput');
  var ph = document.getElementById('aiCampaignPlaceholder');
  btn.textContent = 'Generating...'; btn.disabled = true;
  status.textContent = 'Calling GPT-4o...';
  output.style.display = 'none'; ph.style.display = 'none';
  fetch(API + '/ai-campaigns/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({segment_id:seg})})
    .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(d) {
      btn.textContent = 'Generate Campaign'; btn.disabled = false;
      status.textContent = 'Done - ' + (d.latency_ms/1000).toFixed(1) + 's';
      document.getElementById('aiEmail').textContent = d.email_copy || '';
      var hl = document.getElementById('aiHeadlines'); hl.innerHTML = '';
      (Array.isArray(d.ad_headlines) ? d.ad_headlines : []).forEach(function(h) {
        if (!h) return; var li = document.createElement('li'); li.textContent = h; hl.appendChild(li);
      });
      document.getElementById('aiLanding').textContent = d.landing_page_copy || '';
      document.getElementById('aiSummary').textContent = d.campaign_summary || '';
      output.style.display = 'block';
    })
    .catch(function(e) { btn.textContent = 'Generate Campaign'; btn.disabled = false; status.textContent = 'Error: ' + e.message; ph.style.display = 'block'; });
}

function loadShopifyChart() {
  document.getElementById('shopifyStatus').textContent = 'Loading...';
  fetch(API + '/ai-campaigns/shopify/status')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var m = d.metrics || {};
      document.getElementById('shopifyStatus').textContent = (d.total_orders_logged || 0) + ' orders - ' + new Date().toLocaleTimeString();
      var keys = ['total_orders','total_revenue','new_customers','returning_customers','vip_customers'];
      var clrs = ['rgba(77,159,204,0.85)','rgba(0,230,118,0.85)','rgba(221,0,0,0.85)','rgba(163,98,20,0.85)','rgba(255,200,0,0.85)'];
      var labels = []; var values = []; var bgColors = [];
      keys.forEach(function(k, i) {
        if (typeof m[k] === 'number') {
          labels.push(k.replace(/_/g,' ').replace(/\\b\\w/g, function(c) { return c.toUpperCase(); }));
          values.push(m[k]); bgColors.push(clrs[i]);
        }
      });
      var ctx = document.getElementById('shopifyChart').getContext('2d');
      if (shopifyChart) shopifyChart.destroy();
      shopifyChart = new Chart(ctx, {
        type: 'bar labels: labels, datasets: [{ label: 'Shopify',Colors, borderRadius: 6 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#cce4f0' } } }, scales: { x: { ticks: { color: '#cce4f0' }, grid: { color: 'rgba(255,255,255,0.08)' } }, y: { ticks: { color: '#cce4f0' }, grid: { color: 'rgba(255,255,255,0.08)' } } } }
      });
    })
    .catch(function(e) { document.getElementById('shopifyStatus').textContent = 'Failed: ' + e; });
}

function loadProducts() {
  fetch(API + '/products')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var products = Array.isArray(data) ? data : (data.value || data.data || []);
      document.getElementById('productCount').textContent = products.length;
      var grid = document.getElementById('productGrid'); grid.innerHTML = '';
      products.forEach(function(p) {
        var card = document.createElement('div'); card.className = 'product-card';
        var img = document.createElement('img');
        img.src = p.cloudinary_url || 'https://via.placeholder.com/200';
        img.alt = p.product_name || '';
        img.style.cssText = 'width:100%;height:160px;object-fit:cover;border-radius:6px;margin-bottom:10px;';
        img.onerror = function() { this.src = 'https://via.placeholder.com/200'; };
        var sku = document.createElement('div'); sku.className = 'product-sku'; sku.textContent = p.sku || '';
        var nm = document.createElement('div'); nm.className = 'product-name'; nm.textContent = p.product_name || '';
        var sh = document.createElement('div'); sh.className = 'product-category'; sh.textContent = p.short_description || '';
        var pr = document.createElement('div'); pr.className = 'product-price'; pr.textContent = p.price ? '$' + parseFloat(p.price).toFixed(2) : '';
        card.appendChild(img); card.appendChild(sku); card.appendChild(nm); card.appendChild(sh); card.appendChild(pr);
        grid.appendChild(card);
      });
    })
    .catch(function(e) { console.error('Products failed:', e); });
}

getToken().then(function() { loadProspects(); loadProducts(); loadShopifyChart(); });
</script>
</body>
</html>""")
f.close()
print("Written OK")

import ast, re
html = open("index.html","r",encoding="utf-8").read()
script = html[html.find("<script>")+8:html.rfind("</script>")]
print("Script length:", len(script))
print("Chart block:", repr(script[script.find("shopifyChart = new Chart"):script.find("shopifyChart = new Chart")+120]))
