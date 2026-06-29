"""Export all WooCommerce orders to a CSV file (one row per order).

Pulls every order regardless of status (status=any), paginating until the API
runs out of pages. Line items are summarised into a single column
("sku x qty | sku x qty ..."); core order + billing + totals get their own
columns.
"""

import csv
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

STORE_URL = (os.getenv("WC_STORE_URL") or "").rstrip("/")
AUTH = (os.getenv("WC_CONSUMER_KEY"), os.getenv("WC_CONSUMER_SECRET"))
BASE = f"{STORE_URL}/wp-json/wc/v3"

PER_PAGE = 100

CSV_FIELDS = [
    "id",
    "number",
    "status",
    "date_created",
    "date_paid",
    "date_completed",
    "currency",
    "total",
    "subtotal",
    "total_tax",
    "shipping_total",
    "discount_total",
    "payment_method_title",
    "transaction_id",
    "customer_id",
    "customer_note",
    "created_via",
    "billing_first_name",
    "billing_last_name",
    "billing_company",
    "billing_email",
    "billing_phone",
    "billing_address_1",
    "billing_address_2",
    "billing_city",
    "billing_state",
    "billing_postcode",
    "billing_country",
    "shipping_city",
    "shipping_state",
    "shipping_country",
    "item_count",
    "line_items",
]


def fetch_all_orders():
    page = 1
    while True:
        r = requests.get(
            f"{BASE}/orders",
            auth=AUTH,
            params={"status": "any", "per_page": PER_PAGE, "page": page,
                    "orderby": "date", "order": "asc"},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"Error {r.status_code}: {r.text}", file=sys.stderr)
            sys.exit(1)
        batch = r.json()
        if not batch:
            break
        yield from batch
        if page >= int(r.headers.get("X-WP-TotalPages", page)):
            break
        page += 1


def items_summary(line_items):
    parts = []
    for li in line_items or []:
        ref = li.get("sku") or li.get("name") or li.get("product_id")
        parts.append(f"{ref} x {li.get('quantity')}")
    return " | ".join(parts)


def flatten(o):
    b = o.get("billing") or {}
    s = o.get("shipping") or {}
    items = o.get("line_items") or []
    subtotal = sum(float(li.get("subtotal") or 0) for li in items)
    return {
        "id": o.get("id"),
        "number": o.get("number"),
        "status": o.get("status"),
        "date_created": o.get("date_created"),
        "date_paid": o.get("date_paid"),
        "date_completed": o.get("date_completed"),
        "currency": o.get("currency"),
        "total": o.get("total"),
        "subtotal": f"{subtotal:.2f}",
        "total_tax": o.get("total_tax"),
        "shipping_total": o.get("shipping_total"),
        "discount_total": o.get("discount_total"),
        "payment_method_title": o.get("payment_method_title"),
        "transaction_id": o.get("transaction_id"),
        "customer_id": o.get("customer_id"),
        "customer_note": o.get("customer_note"),
        "created_via": o.get("created_via"),
        "billing_first_name": b.get("first_name"),
        "billing_last_name": b.get("last_name"),
        "billing_company": b.get("company"),
        "billing_email": b.get("email"),
        "billing_phone": b.get("phone"),
        "billing_address_1": b.get("address_1"),
        "billing_address_2": b.get("address_2"),
        "billing_city": b.get("city"),
        "billing_state": b.get("state"),
        "billing_postcode": b.get("postcode"),
        "billing_country": b.get("country"),
        "shipping_city": s.get("city"),
        "shipping_state": s.get("state"),
        "shipping_country": s.get("country"),
        "item_count": sum(int(li.get("quantity") or 0) for li in items),
        "line_items": items_summary(items),
    }


def main():
    if not (STORE_URL and all(AUTH)):
        print("Missing WC_STORE_URL / WC_CONSUMER_KEY / WC_CONSUMER_SECRET in .env",
              file=sys.stderr)
        sys.exit(1)

    out_path = sys.argv[1] if len(sys.argv) > 1 else (
        f"woocommerce_orders_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )

    count = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for o in fetch_all_orders():
            w.writerow(flatten(o))
            count += 1
            if count % 100 == 0:
                print(f"  ...{count} orders")

    print(f"Done. Exported {count} orders to {out_path}")


if __name__ == "__main__":
    main()
