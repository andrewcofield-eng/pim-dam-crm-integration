import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

ai_section = """
<section class="products-section">
  <div class="panel-header">
    <h2>AI Campaign Generator</h2>
    <span class="badge">Segment-Aware</span>
  </div>
  <div class="panel" style="max-width:100%">
    <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;margin-bottom:1.25rem;">
      <label for="segmentSelect" style="font-size:0.9rem;color:var(--text-secondary);">Segment:</label>
      <select id="segmentSelect" class="seg-select">
        <option value="seg_001">seg_001 - High-Value Repeat Buyers</option>
        <option value="seg_002">seg_002 - At-Risk Subscribers</option>
        <option value="seg_003">seg_003 - New Customer Acquisition</option>
      </select>
      <button class="btn-refresh" id="generateBtn" onclick="generateAICampaign()">Generate Campaign</button>
      <span id="aiCampaignStatus" style="font-size:0.82rem;color:var(--text-secondary);"></span>
    </div>
    <div id="aiCampaignPlaceholder" style="color:var(--text-secondary);font-size:0.9rem;padding:1rem 0;">
      Select a segment and click Generate.
    </div>
    <div id="aiCampaignOutput" style="display:none">
      <div class="ai-campaign-grid">
        <div class="ai-block"><h4>Email Copy</h4><p id="aiEmail"></p></div>
        <div class="ai-block"><h4>Ad Headlines</h4><ul id="aiHeadlines"></ul></div>
        <div class="ai-block"><h4>Landing Page Copy</h4><p id="aiLanding"></p></div>
      </div>
      <div class="ai-block" style="margin-top:1rem"><h4>Campaign Summary</h4><p id="aiSummary"></p></div>
    </div>
  </div>
</section>"""

ai_js = """
function generateAICampaign() {
  var seg         = document.getElementById('segmentSelect').value;
  var status      = document.getElementById('aiCampaignStatus');
  var output      = document.getElementById('aiCampaignOutput');
  var placeholder = document.getElementById('aiCampaignPlaceholder');
  var btn         = document.getElementById('generateBtn');
  btn.textContent = 'Generating...';
  btn.disabled    = true;
  status.textContent        = 'Calling GPT-4o...';
  output.style.display      = 'none';
  placeholder.style.display = 'none';
  fetch(API + '/ai-campaigns/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ segment_id: seg })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    document.getElementById('aiEmail').textContent   = d.email_copy || '';
    var ul = document.getElementById('aiHeadlines');
    ul.innerHTML = '';
    var headlines = d.ad_headlines || [];
    if (typeof headlines === 'string') headlines = headlines.split('\\n').filter(Boolean);
    headlines.forEach(function(h) { var li = document.createElement('li'); li.textContent = h; ul.appendChild(li); });
    document.getElementById('aiLanding').textContent = d.landing_page_copy || '';
    document.getElementById('aiSummary').textContent = d.campaign_summary  || '';
    output.style.display      = 'block';
    placeholder.style.display = 'none';
    status.textContent        = 'Campaign ready';
    btn.textContent           = 'Generate Campaign';
    btn.disabled              = false;
  })
  .catch(function(e) {
    status.textContent        = 'Error: ' + e.message;
    placeholder.style.display = 'block';
    btn.textContent           = 'Generate Campaign';
    btn.disabled              = false;
  });
}"""

if 'generateAICampaign' in html:
    print('JS already present - skipping')
else:
    html = html.replace('</script>', ai_js + '\n</script>', 1)
    print('JS injected')

if 'aiCampaignPlaceholder' in html:
    print('HTML section already present - skipping')
else:
    html = html.replace('</body>', ai_section + '\n</body>', 1)
    print('HTML section injected')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Done - index.html updated')
