import requests
import os
from collections import defaultdict

HUBSPOT_API_KEY = "na2-c471-d8c3-4c48-be1a-67e4ad70da1f"
BASE_URL = "https://api.hubapi.com"
headers = {
    "Authorization": "Bearer " + HUBSPOT_API_KEY,
    "Content-Type": "application/json"
}

def get_all_companies():
    """Fetch all companies from HubSpot with pagination."""
    companies = []
    after = None
    while True:
        params = {"limit": 100, "properties": "name,createdate"}
        if after:
            params["after"] = after
        response = requests.get(BASE_URL + "/crm/v3/objects/companies", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        companies.extend(data.get("results", []))
        paging = data.get("paging", {})
        after = paging.get("next", {}).get("after")
        if not after:
            break
    print(f"Fetched {len(companies)} total companies from HubSpot")
    return companies

def delete_company(company_id: str, name: str):
    """Delete a company by ID."""
    response = requests.delete(BASE_URL + "/crm/v3/objects/companies/" + company_id, headers=headers)
    if response.status_code == 204:
        print(f"  🗑️  Deleted duplicate: {name} (ID: {company_id})")
    else:
        print(f"  ⚠️  Failed to delete {name} (ID: {company_id}): {response.status_code}")

def cleanup_duplicates(dry_run=True):
    """Find duplicate companies by name and delete all but the oldest."""
    companies = get_all_companies()

    # Group by name
    by_name = defaultdict(list)
    for c in companies:
        name = c["properties"].get("name", "").strip()
        created = c["properties"].get("createdate", "")
        if name:
            by_name[name].append({"id": c["id"], "name": name, "created": created})

    # Find duplicates
    duplicates_found = 0
    for name, entries in by_name.items():
        if len(entries) > 1:
            # Sort oldest first (keep oldest, delete the rest)
            entries.sort(key=lambda x: x["created"])
            keeper = entries[0]
            dupes = entries[1:]
            duplicates_found += len(dupes)
            print(f"\n📋 '{name}' — {len(entries)} copies found, keeping ID: {keeper['id']} (created: {keeper['created']})")
            for dupe in dupes:
                if dry_run:
                    print(f"  [DRY RUN] Would delete: {dupe['name']} (ID: {dupe['id']}, created: {dupe['created']})")
                else:
                    delete_company(dupe["id"], dupe["name"])

    if duplicates_found == 0:
        print("\n✅ No duplicates found — CRM is clean!")
    else:
        print(f"\n{'[DRY RUN] Would delete' if dry_run else 'Deleted'} {duplicates_found} duplicate companies.")

if __name__ == "__main__":
    # Step 1: Run with dry_run=True first to preview what will be deleted
    # Step 2: Change to dry_run=False to actually delete
    cleanup_duplicates(dry_run=True)