import os
import sys
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

# If your 'collection' taxonomy is registered as public and show_in_rest => true,
# it is readable publicly at /wp-json/wp/v2/collection.
# If restricted, provide an Application Password user/pass:
WP_USER = ""
WP_APP_PASSWORD = ""

OUTPUT_MD_FILE = "STORE_ARCHITECTURE_DEEP_DIVE.md"

# ==============================================================================
# API HELPERS
# ==============================================================================
session = requests.Session()
if WP_USER and WP_APP_PASSWORD:
    session.auth = (WP_USER, WP_APP_PASSWORD)

def get_paged_data(endpoint, params=None):
    """Fetch all pages from a REST endpoint."""
    if params is None:
        params = {}
    params['per_page'] = 100
    params['page'] = 1

    all_data = []
    while True:
        try:
            auth = (WC_CONSUMER_KEY, WC_CONSUMER_SECRET) if "/wc/v3/" in endpoint else None
            response = session.get(endpoint, params=params, auth=auth, timeout=30)

            if response.status_code == 404:
                print(f"[!] Warning: 404 Not Found on {endpoint}")
                break
            response.raise_for_status()

            data = response.json()
            if not data or not isinstance(data, list):
                break

            all_data.extend(data)

            total_pages = int(response.headers.get("X-WP-TotalPages", 1))
            if params['page'] >= total_pages:
                break
            params['page'] += 1

        except Exception as e:
            print(f"[!] Error fetching {endpoint}: {e}")
            break

    return all_data

# ==============================================================================
# DATA COLLECTORS
# ==============================================================================
print(f"[*] Connecting to {SITE_URL}...")

# 1. Fetch WooCommerce Product Categories
print("[*] Fetching WooCommerce Product Categories (product_cat)...")
wc_categories = get_paged_data(f"{SITE_URL}/wp-json/wc/v3/products/categories")

# 2. Fetch Custom 'collection' Taxonomy
print("[*] Fetching Custom Taxonomy 'collection'...")
collections = get_paged_data(f"{SITE_URL}/wp-json/wp/v2/collection")

# If wp/v2/collection failed, fall back to checking if it's registered differently
if not collections:
    print("[?] Checking fallback wp/v2/taxonomies...")
    tax_info = session.get(f"{SITE_URL}/wp-json/wp/v2/taxonomies").json()
    if 'collection' in tax_info:
        rest_base = tax_info['collection'].get('rest_base', 'collection')
        collections = get_paged_data(f"{SITE_URL}/wp-json/wp/v2/{rest_base}")

# 3. Fetch Products Sample (up to 100 products for relationship mapping)
print("[*] Fetching WooCommerce Products for taxonomy cross-referencing...")
products = get_paged_data(f"{SITE_URL}/wp-json/wc/v3/products", params={"per_page": 100})

# ==============================================================================
# BUILD TAXONOMY TREES
# ==============================================================================
def build_hierarchy_tree(term_list):
    """Organizes flat list of terms into parent -> children map."""
    by_id = {t['id']: t for t in term_list}
    children_map = defaultdict(list)
    top_level = []

    for t in term_list:
        parent_id = t.get('parent', 0)
        if parent_id == 0 or parent_id not in by_id:
            top_level.append(t)
        else:
            children_map[parent_id].append(t)

    return by_id, children_map, top_level

cat_by_id, cat_children_map, cat_top_level = build_hierarchy_tree(wc_categories)
col_by_id, col_children_map, col_top_level = build_hierarchy_tree(collections)

# Map products to collections and categories
product_col_map = defaultdict(list)
product_cat_map = defaultdict(list)

for p in products:
    p_id = p['id']
    p_name = p['name']
    
    # Categories
    for c in p.get('categories', []):
        product_cat_map[p_id].append(c['name'])

    # Collections (from custom fields, tags, or taxonomy if returned)
    # Checking for collection term IDs in custom attributes or WP REST endpoint
    if 'collection' in p:
        for col_id in p['collection']:
            product_col_map[col_id].append(p_name)

# ==============================================================================
# GENERATE MARKDOWN REPORT
# ==============================================================================
print(f"[*] Generating {OUTPUT_MD_FILE}...")

md = []
md.append(f"# Deep Architecture Report: {SITE_URL}\n")
md.append("This document explains the data model, taxonomies, and hierarchy relationships found in this WooCommerce store.\n")

# SECTION 1: EXECUTIVE TAXONOMY ARCHITECTURE
md.append("## 1. Taxonomy Architecture Overview\n")
md.append("| Metric | Count Found |")
md.append("| :--- | :--- |")
md.append(f"| **Total WooCommerce Product Categories (`product_cat`)** | {len(wc_categories)} |")
md.append(f"| **Total Custom Collection Terms (`collection`)** | {len(collections)} |")
md.append(f"| **Sampled Products** | {len(products)} |\n")

# SECTION 2: 'COLLECTION' TAXONOMY HIERARCHY
md.append("## 2. 'Collection' Taxonomy Breakdown (Selections & Child Collections)\n")
md.append("In your site, this taxonomy acts as a 2-tier system:")
md.append("- **Top Level (Parent Collections / 'Selections')**: Rendered on `/all-selections/`")
md.append("- **Leaf / Child Collections**: Rendered on `/collection/{slug}/` via `[bigtree_collection_grid]` or `[bigtree_collection_products]`\n")

if collections:
    md.append("### Tree Structure:\n")
    for parent in sorted(col_top_level, key=lambda x: x['name']):
        child_count = len(col_children_map.get(parent['id'], []))
        md.append(f"- **{parent['name']}** (`ID: {parent['id']}`, `Slug: {parent['slug']}`) — *Children: {child_count}*")
        for child in sorted(col_children_map.get(parent['id'], []), key=lambda x: x['name']):
            md.append(f"  - ↳ **{child['name']}** (`ID: {child['id']}`, `Slug: {child['slug']}`) — *Count: {child.get('count', 0)} products*")
    md.append("\n")
else:
    md.append("> **Note:** `/wp-json/wp/v2/collection` returned 0 terms or was not exposed to the REST API. Ensure `show_in_rest => true` is set in its registration, or run with WP credentials.\n")

# SECTION 3: WOOCOMMERCE PRODUCT CATEGORIES
md.append("## 3. Product Categories Breakdown (`product_cat`)\n")
md.append("These are standard WooCommerce categories used for top navigation buttons and card badges:\n")

for parent in sorted(cat_top_level, key=lambda x: x['name']):
    child_count = len(cat_children_map.get(parent['id'], []))
    md.append(f"- **{parent['name']}** (`ID: {parent['id']}`, `Slug: {parent['slug']}`) — *Count: {parent.get('count', 0)}*")
    for child in sorted(cat_children_map.get(parent['id'], []), key=lambda x: x['name']):
        md.append(f"  - ↳ **{child['name']}** (`ID: {child['id']}`, `Slug: {child['slug']}`) — *Count: {child.get('count', 0)}*")
md.append("\n")

# SECTION 4: CODE LOGIC AUDIT
md.append("## 4. Code Logic Cross-Audit (From Your Snippets)\n")
md.append("### A. What happens on `/all-selections/`:")
md.append("1. Displays parent terms of `collection`.")
md.append("2. Under each parent (e.g. `DK SELECTION`), it runs `bigtree_get_collection_child_categories()`.")
md.append("3. That helper finds all descendant products, finds their `product_cat` terms where `parent != 0`, and prints: `Leather, Fabric`.")
md.append("4. The top filter buttons filter these parent selection cards.\n")

md.append("### B. What happens on `/collection/{slug}/` (e.g., `/collection/dk-selection/`):")
md.append("1. The page queries the current term (e.g., `dk-selection`).")
md.append("2. If the term has child terms, `[bigtree_collection_grid]` displays cards for each child collection (e.g. `ABI`, `ABYSSAL`).")
md.append("3. If it has no children (it is a leaf collection), `[bigtree_collection_products]` displays the individual products.\n")

# SECTION 5: WHAT YOUR TASK REQUIRES
md.append("## 5. What is Required For The Dynamic Filters Task\n")
md.append("To replicate the filter bar from `/all-selections/` onto `/collection/dk-selection/`:")
md.append("1. **Discover Available Filter Tabs:** For the current collection, find only the categories present in its children (e.g., If DK Selection only contains Leather & Fabric, only show [ALL] [LEATHER] [FABRIC]).")
md.append("2. **Tag Each Card:** Each child collection card or product card needs a `data-category='[\"leather\", \"fabric\"]'` HTML attribute or class name.")
md.append("3. **Filter Trigger:** When clicking a filter button (e.g. `FABRIC`), JavaScript hides cards that do not match, or an AJAX call updates the grid.\n")

with open(OUTPUT_MD_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"[✔] Report successfully generated: {OUTPUT_MD_FILE}")
