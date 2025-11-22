from woocommerce import API
import json
from typing import Optional, Dict


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


def get_product(store_url: str, consumer_key: str, consumer_secret: str, product_id: int) -> Optional[Dict]:
    wc_api = WooCommerceProductAPI(store_url, consumer_key, consumer_secret)  # Initialize API
    product = wc_api.get_product_by_id(product_id)
    return product

