import requests
import time, os
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Configuration ---
load_dotenv()

SITE_URL = os.getenv("WC_STORE_URL")
CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

def create_resilient_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Connection": "close"
    })
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "PUT", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_media_alt(session, img_id):
    """Read the true alt text from the WP media endpoint (more reliable than WC images field)."""
    try:
        resp = session.get(
            f"{SITE_URL}/wp-json/wp/v2/media/{img_id}",
            auth=(CONSUMER_KEY, CONSUMER_SECRET),
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json().get('alt_text', '')
    except requests.exceptions.RequestException as e:
        print(f"    [WARNING] Could not fetch alt for media ID {img_id}: {e}")
    return None  # None = unknown, treat as needs update to be safe

def generate_image_alts():
    session = create_resilient_session()
    page = 1
    per_page = 50

    print("Starting Resilient Bulk Alt-Text Generation...")

    while True:
        print(f"\n--- Fetching Page {page} ---")
        endpoint = f"{SITE_URL}/wp-json/wc/v3/products"

        params = {
            "per_page": per_page,
            "page": page,
            "_fields": "id,name,categories,images"
        }

        try:
            response = session.get(
                endpoint,
                auth=(CONSUMER_KEY, CONSUMER_SECRET),
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                print(f"[ERROR] Failed to fetch page {page}. Status: {response.status_code}")
                time.sleep(5)
                continue

            products = response.json()

            if not products:
                print("\n[COMPLETE] Finished processing all products.")
                break

            for product in products:
                product_id = product.get('id')
                name = product.get('name', 'Product')
                categories = product.get('categories', [])
                images = product.get('images', [])

                if not images:
                    continue

                primary_category = categories[0]['name'] if categories else "Uncategorized"
                target_alt_text = f"{name} | {primary_category}"

                updated_images = []
                needs_update = False

                for img in images:
                    img_id = img['id']

                    # Read alt from WP media endpoint — WC images field is unreliable
                    current_alt = get_media_alt(session, img_id)

                    if current_alt is None or current_alt != target_alt_text:
                        needs_update = True

                    updated_images.append({
                        "id": img_id,
                        "alt": target_alt_text
                    })

                if needs_update:
                    update_endpoint = f"{SITE_URL}/wp-json/wc/v3/products/{product_id}"
                    update_payload = {"images": updated_images}

                    try:
                        update_req = session.put(
                            update_endpoint,
                            auth=(CONSUMER_KEY, CONSUMER_SECRET),
                            json=update_payload,
                            timeout=30
                        )

                        if update_req.status_code in [200, 201]:
                            print(f"[SUCCESS] ID {product_id} | Alt updated to: '{target_alt_text}'")
                        else:
                            print(f"[ERROR] ID {product_id} | Update failed. Status: {update_req.status_code} | {update_req.text}")

                    except requests.exceptions.RequestException as pe:
                        print(f"[WARNING] ID {product_id} | Skipped due to connection error: {str(pe)}")
                        continue

                else:
                    print(f"[SKIP] ID {product_id} | All alts already correct: '{target_alt_text}'")

            page += 1
            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Page {page} failed due to network issue: {str(e)}")
            page += 1
            time.sleep(5)

if __name__ == "__main__":
    generate_image_alts()
