import requests
import time, os
from dotenv import load_dotenv

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

SITE_URL = os.getenv("WC_STORE_URL")
CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

def create_resilient_session():
    """Configure a requests session with automatic retries and browser headers."""
    session = requests.Session()
    
    # Mask as a standard browser and disable Keep-Alive to prevent EOF drops
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Connection": "close"
    })
    
    # Configure exponential backoff for 500-level errors and connection drops
    retries = Retry(
        total=5,
        backoff_factor=2, # Wait 2s, 4s, 8s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "PUT", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

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
                # Wait before trying the next page in case of severe rate limiting
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
                    current_alt = img.get('alt', '')
                    if current_alt != target_alt_text:
                        needs_update = True
                        
                    updated_images.append({
                        "id": img['id'],
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
                        # Continue to the next product despite this failure
                        continue
                        
                else:
                    print(f"[SKIP] ID {product_id} | Alt text already matches: '{target_alt_text}'")
                    
            page += 1
            time.sleep(1) 

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Page {page} failed due to network issue: {str(e)}")
            # Increment page to prevent infinite loops on a permanently dead page
            page += 1
            time.sleep(5)

if __name__ == "__main__":
    generate_image_alts()
