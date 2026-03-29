import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Print a diagnostic snapshot of key markers
markers = [
    'generateAICampaign',
    'aiCampaignPlaceholder',
    'aiCampaignOutput',
    'aiEmail',
    'aiSummary',
    'segmentSelect',
    'campaignOutput',
    'campaignText',
    'ai-campaigns/generate',
    'const API',
    'var API',
]

print("=== index.html diagnostic ===")
for m in markers:
    count = content.count(m)
    print(f"  {m}: {count} occurrence(s)")

print(f"\nTotal file length: {len(content)} chars")
