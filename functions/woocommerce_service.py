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



def get_product(store_url: str, consumer_key: str, consumer_secret: str, product_id: int) -> Optional[Dict]:
    wc_api = WooCommerceProductAPI(store_url, consumer_key, consumer_secret)  # Initialize API
    product = wc_api.get_product_by_id(product_id)

    # with open(f'product_data_{product_id}.json', 'w') as f:
    #     json.dump(product, f, indent=2)

    return product



# print("\n" + "="*50)
# print(f"Product ID: {product.get('id')}")
# print(f"Name: {product.get('name')}")
# print(f"SKU: {product.get('sku')}")
# print(f"Price: ${product.get('price')}")
# print(f"Regular Price: ${product.get('regular_price')}")
# print(f"Sale Price: ${product.get('sale_price')}")
# print(f"Stock Status: {product.get('stock_status')}")
# print(f"Stock Quantity: {product.get('stock_quantity')}")
# print(f"Categories: {[cat['name'] for cat in product.get('categories', [])]}")
# print(f"Tags: {[tag['name'] for tag in product.get('tags', [])]}")
# print(f"Description: {product.get('description', '')[:100]}...")
# print("="*50 + "\n")

