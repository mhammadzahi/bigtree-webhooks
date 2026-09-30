import sys, os
import json
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SITE_URL = os.getenv("BT_WC_STORE_URL")
WC_CONSUMER_KEY = os.getenv("BT_WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("BT_WC_CONSUMER_SECRET")

print(SITE_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET)




OUTPUT_MD_FILE = "ALL_COLLECTIONS_HIERARCHY.md"

session = requests.Session()

print(f"[*] Connecting to {SITE_URL}...")
print("[*] Fetching ALL terms from taxonomy 'collection'...")

all_terms = []
page = 1

while True:
    try:
        url = f"{SITE_URL}/wp-json/wp/v2/collection"
        params = {
            "per_page": 100,
            "page": page
        }

        # 1. Try public request first (WP taxonomy terms are public)
        res = session.get(url, params=params, timeout=30)

        # 2. Fallback: If restricted, pass credentials via query params
        if res.status_code in [401, 403]:
            params["consumer_key"] = WC_CONSUMER_KEY
            params["consumer_secret"] = WC_CONSUMER_SECRET
            res = session.get(url, params=params, timeout=30)

        # 3. Check for errors
        if res.status_code == 400: # Usually means page exceeds total pages
            break

        res.raise_for_status()
        data = res.json()

        if not data or not isinstance(data, list):
            break

        all_terms.extend(data)
        total_pages = int(res.headers.get("X-WP-TotalPages", 1))
        total_terms = res.headers.get("X-WP-Total", "unknown")

        print(f"    [✓] Page {page}/{total_pages} loaded ({len(all_terms)}/{total_terms} terms)...")

        if page >= total_pages:
            break
        page += 1

    except Exception as e:
        print(f"[!] Stopped on page {page}. Reason: {e}")
        break

print(f"\n[✔] Successfully fetched {len(all_terms)} total terms from WordPress!")

if len(all_terms) == 0:
    print("[!] No terms found. Please ensure the taxonomy endpoint is active.")
    sys.exit()

# ==============================================================================
# RECONSTRUCT HIERARCHY TREE (Matching WP Admin '—' and '— —')
# ==============================================================================
terms_by_id = {t['id']: t for t in all_terms}
children_by_parent = defaultdict(list)

for t in all_terms:
    parent_id = t.get('parent', 0)
    children_by_parent[parent_id].append(t)

# Sort alphabetically
for pid in children_by_parent:
    children_by_parent[pid].sort(key=lambda x: x['name'])

# Roots are terms with parent = 0 or parent not found
top_level_selections = [t for t in all_terms if t.get('parent', 0) == 0 or t.get('parent') not in terms_by_id]
top_level_selections.sort(key=lambda x: x['name'])

depth_map = {}
max_depth = 0
leaf_terms = []
parent_terms = []

def calculate_depth(term_id, current_depth):
    global max_depth
    if current_depth > max_depth:
        max_depth = current_depth
    depth_map[term_id] = current_depth

    children = children_by_parent.get(term_id, [])
    if children:
        parent_terms.append(term_id)
        for child in children:
            calculate_depth(child['id'], current_depth + 1)
    else:
        leaf_terms.append(term_id)

for root in top_level_selections:
    calculate_depth(root['id'], 0)

# ==============================================================================
# GENERATE MARKDOWN
# ==============================================================================
print(f"[*] Generating {OUTPUT_MD_FILE}...")

md = []
md.append("# Full Collection Taxonomy Hierarchy Report\n")
md.append(f"**Target Site:** `{SITE_URL}`  ")
md.append(f"**Total Collection Terms:** `{len(all_terms)}`  ")
md.append(f"**Top-Level Selections (Roots):** `{len(top_level_selections)}`  ")
md.append(f"**Max Hierarchy Depth:** `Level {max_depth}`  ")
md.append(f"**Parent Terms (Has Children / Grid View):** `{len(parent_terms)}`  ")
md.append(f"**Leaf Terms (Has Products Directly):** `{len(leaf_terms)}`  \n")

md.append("## Legend (Matching WP Admin)")
md.append("- **Root**: Top-level brand / master selection (e.g. `AZ Selection`, `BNT Selection`).")
md.append("- `—`: Level 1 Child (e.g. `— 3D-Printed Lighting`).")
md.append("- `— —`: Level 2 Child (e.g. `— — Fluid`, `— — Nie`).")
md.append("- `— — —`: Level 3 Child.\n")

md.append("---")
md.append("## Complete Hierarchy Tree\n")

def render_branch(term, depth):
    tid = term['id']
    tname = term['name']
    tslug = term['slug']
    count = term.get('count', 0)
    children = children_by_parent.get(tid, [])

    if depth == 0:
        badge = f"**[ROOT | {len(children)} direct children]**"
        md.append(f"### {tname} (`ID: {tid}`, `slug: {tslug}`) {badge}")
    else:
        indent = "  " * (depth - 1)
        dash = "— " * depth
        node_status = f"`[PARENT: {len(children)} sub-children]`" if children else f"`[LEAF: {count} products]`"
        md.append(f"{indent}- **{dash}{tname}** (`ID: {tid}`, `slug: {tslug}`) — {node_status}")

    for child in children:
        render_branch(child, depth + 1)

for root in top_level_selections:
    render_branch(root, 0)
    md.append("")

md.append("---\n")
md.append("## Multi-Tier Summary\n")
md.append("| Master Selection | Direct Children | Max Sub-Depth | Type |")
md.append("| :--- | :--- | :--- | :--- |")

for root in top_level_selections:
    children = children_by_parent.get(root['id'], [])
    sub_depths = [depth_map.get(c['id'], 1) for c in children]
    max_sub = max(sub_depths) if sub_depths else 0
    has_sub = sum(1 for c in children if len(children_by_parent.get(c['id'], [])) > 0)
    
    type_str = "Flat (Direct Leaves)" if has_sub == 0 else f"Multi-Tier ({has_sub} intermediate folders)"
    md.append(f"| **{root['name']}** | {len(children)} | Level {max_sub} | {type_str} |")

with open(OUTPUT_MD_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"[✔] Successfully created: {OUTPUT_MD_FILE}")
