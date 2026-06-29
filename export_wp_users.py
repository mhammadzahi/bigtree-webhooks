"""Export all WordPress/WooCommerce users to a CSV file.

Uses the WooCommerce REST API customers endpoint with role=all, which returns
every WP user regardless of role (admin, customer, subscriber, etc.).
"""

import csv
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from woocommerce import API

load_dotenv()

STORE_URL = os.getenv("WC_STORE_URL")
CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

PER_PAGE = 100  # WooCommerce max page size

CSV_FIELDS = [
    "id",
    "date_created",
    "email",
    "first_name",
    "last_name",
    "username",
    "role",
    "is_paying_customer",
    "billing_company",
    "billing_phone",
    "billing_city",
    "billing_country",
]


def fetch_all_users(wcapi):
    """Yield every user, paginating until the API runs out of pages."""
    page = 1
    while True:
        response = wcapi.get(
            "customers",
            params={"role": "all", "per_page": PER_PAGE, "page": page},
        )
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}", file=sys.stderr)
            sys.exit(1)

        batch = response.json()
        if not batch:
            break

        yield from batch

        total_pages = int(response.headers.get("X-WP-TotalPages", page))
        if page >= total_pages:
            break
        page += 1


def flatten(user):
    billing = user.get("billing") or {}
    return {
        "id": user.get("id"),
        "date_created": user.get("date_created"),
        "email": user.get("email"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "username": user.get("username"),
        "role": user.get("role"),
        "is_paying_customer": user.get("is_paying_customer"),
        "billing_company": billing.get("company"),
        "billing_phone": billing.get("phone"),
        "billing_city": billing.get("city"),
        "billing_country": billing.get("country"),
    }


def main():
    if not all([STORE_URL, CONSUMER_KEY, CONSUMER_SECRET]):
        print(
            "Missing WC_STORE_URL / WC_CONSUMER_KEY / WC_CONSUMER_SECRET in .env",
            file=sys.stderr,
        )
        sys.exit(1)

    wcapi = API(
        url=STORE_URL,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        version="wc/v3",
        timeout=30,
    )

    out_path = sys.argv[1] if len(sys.argv) > 1 else (
        f"wp_users_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )

    count = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for user in fetch_all_users(wcapi):
            writer.writerow(flatten(user))
            count += 1
            if count % 100 == 0:
                print(f"  ...exported {count} users")

    print(f"Done. Exported {count} users to {out_path}")


if __name__ == "__main__":
    main()
