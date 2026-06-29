"""Export one full product row per WooCommerce category.

For every non-empty product category, picks one representative product and
writes its full record: all WooCommerce core product fields plus every ACF /
custom field (these arrive flat in the REST `meta_data` array, the same data
stored in wp_postmeta).

Columns are built dynamically: a fixed set of core product fields, then the
union of every meta/ACF key seen across the selected products. Internal,
underscore-prefixed meta keys (ACF field-key refs, plugin internals) are
excluded by default; pass --include-internal to keep them.
"""

import csv
import html
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

STORE_URL = (os.getenv("WC_STORE_URL") or "").rstrip("/")
AUTH = (os.getenv("WC_CONSUMER_KEY"), os.getenv("WC_CONSUMER_SECRET"))
BASE = f"{STORE_URL}/wp-json/wc/v3"

PER_PAGE = 100
INCLUDE_INTERNAL = "--include-internal" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]

# Core product fields, in export order. (Category context first.)
CORE_FIELDS = [
    "source_category_id",
    "source_category_name",
    "source_category_parent",
    "id",
    "sku",
    "name",
    "slug",
    "permalink",
    "type",
    "status",
    "featured",
    "catalog_visibility",
    "description",
    "short_description",
    "price",
    "regular_price",
    "sale_price",
    "on_sale",
    "tax_status",
    "tax_class",
    "manage_stock",
    "stock_quantity",
    "stock_status",
    "backorders",
    "weight",
    "length",
    "width",
    "height",
    "shipping_class",
    "categories",
    "tags",
    "brands",
    "attributes",
    "date_created",
    "date_modified",
]
CORE_SET = set(CORE_FIELDS)


def get(path, **params):
    r = requests.get(f"{BASE}/{path}", auth=AUTH, params=params, timeout=30)
    if r.status_code != 200:
        print(f"Error {r.status_code} on {path}: {r.text}", file=sys.stderr)
        sys.exit(1)
    return r


def fetch_all(path, **extra):
    page = 1
    while True:
        r = get(path, per_page=PER_PAGE, page=page, **extra)
        batch = r.json()
        if not batch:
            break
        yield from batch
        if page >= int(r.headers.get("X-WP-TotalPages", page)):
            break
        page += 1


def join_names(items):
    return " | ".join(html.unescape(i.get("name", "")) for i in items or [])


def attrs_str(attrs):
    parts = []
    for a in attrs or []:
        opts = ", ".join(a.get("options") or [])
        parts.append(f"{a.get('name')}: {opts}")
    return " || ".join(parts)


def core_row(product, cat, cat_name_by_id):
    dims = product.get("dimensions") or {}
    return {
        "source_category_id": cat["id"],
        "source_category_name": html.unescape(cat["name"]),
        "source_category_parent": cat_name_by_id.get(cat.get("parent"), ""),
        "id": product.get("id"),
        "sku": product.get("sku"),
        "name": html.unescape(product.get("name", "")),
        "slug": product.get("slug"),
        "permalink": product.get("permalink"),
        "type": product.get("type"),
        "status": product.get("status"),
        "featured": product.get("featured"),
        "catalog_visibility": product.get("catalog_visibility"),
        "description": product.get("description"),
        "short_description": product.get("short_description"),
        "price": product.get("price"),
        "regular_price": product.get("regular_price"),
        "sale_price": product.get("sale_price"),
        "on_sale": product.get("on_sale"),
        "tax_status": product.get("tax_status"),
        "tax_class": product.get("tax_class"),
        "manage_stock": product.get("manage_stock"),
        "stock_quantity": product.get("stock_quantity"),
        "stock_status": product.get("stock_status"),
        "backorders": product.get("backorders"),
        "weight": product.get("weight"),
        "length": dims.get("length"),
        "width": dims.get("width"),
        "height": dims.get("height"),
        "shipping_class": product.get("shipping_class"),
        "categories": join_names(product.get("categories")),
        "tags": join_names(product.get("tags")),
        "brands": join_names(product.get("brands")),
        "attributes": attrs_str(product.get("attributes")),
        "date_created": product.get("date_created"),
        "date_modified": product.get("date_modified"),
    }


def meta_dict(product):
    out = {}
    for m in product.get("meta_data") or []:
        key = m.get("key", "")
        if not key:
            continue
        if key.startswith("_") and not INCLUDE_INTERNAL:
            continue
        val = m.get("value")
        if isinstance(val, (list, dict)):
            val = str(val)
        # Avoid clobbering core columns (e.g. ACF "type"/"weight" vs WC core)
        if key in CORE_SET:
            key = f"meta_{key}"
        out[key] = val
    return out


def main():
    if not (STORE_URL and all(AUTH)):
        print("Missing WC_STORE_URL / WC_CONSUMER_KEY / WC_CONSUMER_SECRET in .env",
              file=sys.stderr)
        sys.exit(1)

    out_path = ARGS[0] if ARGS else (
        f"category_products_full_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )

    print("Pulling all product categories...")
    categories = list(fetch_all("products/categories"))
    cat_name_by_id = {c["id"]: html.unescape(c["name"]) for c in categories}
    todo = [c for c in categories if c.get("count")]
    print(f"  {len(categories)} categories, {len(todo)} non-empty")

    rows = []
    meta_keys = set()
    done = 0
    print(f"Fetching one full product per category...")
    for c in todo:
        # list endpoint returns the full product object incl. meta_data
        items = get("products", per_page=1, category=c["id"]).json()
        if not items:
            continue
        p = items[0]
        meta = meta_dict(p)
        meta_keys.update(meta.keys())
        row = core_row(p, c, cat_name_by_id)
        row.update(meta)
        rows.append(row)
        done += 1
        if done % 50 == 0:
            print(f"  ...{done}/{len(todo)}")
        time.sleep(0.05)

    fieldnames = CORE_FIELDS + sorted(meta_keys)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Done. {len(rows)} rows, {len(fieldnames)} columns "
          f"({len(meta_keys)} ACF/meta) -> {out_path}")


if __name__ == "__main__":
    main()
