from woocommerce import API
import json
from typing import Optional, Dict, List


class WooCommerceProductAPI:
    
    def __init__(self, url: str, consumer_key: str, consumer_secret: str):
        self.wcapi = API(url=url, consumer_key=consumer_key, consumer_secret=consumer_secret, version="wc/v3", timeout=15)
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        try:
            response = self.wcapi.get(f"products/{product_id}")
            
            if response.status_code == 200:
                return response.json()

            else:
                print(f"Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return None


def get_default_product_id(store_url: str, consumer_key: str, consumer_secret: str, product_id: int) -> Optional[int]:
    wc_api = WooCommerceProductAPI(store_url, consumer_key, consumer_secret)  # Initialize API
    print(f"\n--- Checking Product ID: {product_id} ---")
    product_data = wc_api.get_product_by_id(product_id)

    if not product_data:
        return None # The API class already prints an error, so we just return


    product_type = product_data.get('type')

    if product_type == 'variable':
        # It's a parent product. The default is the first available variation.
        variations = product_data.get('variations', [])
        if variations:
            default_variation_id = variations[0]
            print(f"Type is 'variable'. Found default variation ID: {default_variation_id}")
            return default_variation_id
        else:
            print(f"[None] Type is 'variable', but it has no variations.")
            return None
    
    elif product_type in ['simple', 'variation']:
        # It's already a specific, purchasable product.
        print(f"Type is '{product_type}'. Returning its own ID: {product_id}")
        return product_id
        
    else:
        # Handle other potential types like 'grouped', 'external' etc.
        print(f"Product type is '{product_type}'. This is not a standard purchasable item. Returning its own ID.")
        return product_id



def get_product(store_url: str, consumer_key: str, consumer_secret: str, product_id: int) -> Optional[Dict]:
    wc_api = WooCommerceProductAPI(store_url, consumer_key, consumer_secret)  # Initialize API
    product = wc_api.get_product_by_id(product_id)
    return product

