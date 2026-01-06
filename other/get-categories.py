from woocommerce import API
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get WooCommerce credentials from .env
WC_STORE_URL = os.getenv('WC_STORE_URL')
WC_CONSUMER_KEY = os.getenv('WC_CONSUMER_KEY')
WC_CONSUMER_SECRET = os.getenv('WC_CONSUMER_SECRET')

# Initialize WooCommerce API
wcapi = API(
    url=WC_STORE_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=15
)

def get_subcategories(parent_id):
    """Retrieve subcategories for a given parent category"""
    try:
        response = wcapi.get("products/categories", params={"parent": parent_id, "per_page": 100})
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching subcategories: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return []

def get_parent_categories():
    """Retrieve all parent categories (categories with parent=0) and their subcategories"""
    try:
        # Get all categories with parent=0 (parent categories only)
        response = wcapi.get("products/categories", params={"parent": 0, "per_page": 100})
        
        if response.status_code == 200:
            categories = response.json()
            print(f"Found {len(categories)} parent categories:\n")
            
            for category in categories:
                print(f"ID: {category['id']}")
                print(f"Name: {category['name']}")
                print(f"Slug: {category['slug']}")
                print(f"Count: {category['count']} products")
                
                # Only get subcategories for Furniture category
                if category['name'] == 'Furniture':
                    subcategories = get_subcategories(category['id'])
                    if subcategories:
                        print(f"  Subcategories ({len(subcategories)}):")
                        for sub in subcategories:
                            print(f"    - ID: {sub['id']}, Name: {sub['name']}, Slug: {sub['slug']}, Count: {sub['count']} products")
                
                print("-" * 50)
            
            return categories
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

if __name__ == "__main__":
    print("Retrieving parent categories from WooCommerce store...\n")
    categories = get_parent_categories()
    
    if categories:
        print(f"\n✓ Successfully retrieved {len(categories)} parent categories")
    else:
        print("\n✗ Failed to retrieve categories")
