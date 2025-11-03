from woocommerce import API
import json
from typing import Optional, Dict, List

class WooCommerceProductAPI:
    
    def __init__(self, url: str, consumer_key: str, consumer_secret: str):
        self.wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=30
        )
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """
        Retrieve a single product by ID
        
        Args:
            product_id: The WooCommerce product ID
            
        Returns:
            Dictionary containing product data or None if error
        """
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
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict]:
        """
        Retrieve a product by SKU

        Args:
            sku: The product SKU
            
        Returns:
            Dictionary containing product data or None if error
        """
        try:
            response = self.wcapi.get("products", params={"sku": sku})
            
            if response.status_code == 200:
                products = response.json()
                if products:
                    return products[0]  # Return first matching product
                else:
                    print(f"No product found with SKU: {sku}")
                    return None
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return None


    def get_all_products(self, per_page: int = 10, page: int = 1) -> List[Dict]:
        """
        Retrieve multiple products with pagination
        
        Args:
            per_page: Number of products per page (max 100)
            page: Page number
            
        Returns:
            List of product dictionaries
        """
        try:
            response = self.wcapi.get("products", params={
                "per_page": per_page,
                "page": page
            })
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return []
    
    def search_products(self, search_term: str, per_page: int = 10) -> List[Dict]:
        """
        Search for products by name or description
        
        Args:
            search_term: The search keyword
            per_page: Number of results to return
            
        Returns:
            List of matching product dictionaries
        """
        try:
            response = self.wcapi.get("products", params={
                "search": search_term,
                "per_page": per_page
            })
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return []
    
    def print_product_info(self, product: Dict):
        """
        Pretty print product information
        
        Args:
            product: Product dictionary
        """
        if not product:
            print("No product data to display")
            return
        
        print("\n" + "="*50)
        print(f"Product ID: {product.get('id')}")
        print(f"Name: {product.get('name')}")
        print(f"SKU: {product.get('sku')}")
        print(f"Price: ${product.get('price')}")
        print(f"Regular Price: ${product.get('regular_price')}")
        print(f"Sale Price: ${product.get('sale_price')}")
        print(f"Stock Status: {product.get('stock_status')}")
        print(f"Stock Quantity: {product.get('stock_quantity')}")
        print(f"Categories: {[cat['name'] for cat in product.get('categories', [])]}")
        print(f"Tags: {[tag['name'] for tag in product.get('tags', [])]}")
        print(f"Description: {product.get('description', '')[:100]}...")
        print("="*50 + "\n")


def main():
    # Configuration - Replace with your actual credentials
    STORE_URL = "https://yallaiot.com"
    CONSUMER_KEY = ""
    CONSUMER_SECRET = ""
    
    # Initialize API
    wc_api = WooCommerceProductAPI(STORE_URL, CONSUMER_KEY, CONSUMER_SECRET)
    
    # Example 1: Get product by ID
    print("Example 1: Get Product by ID")
    product_id = 1822
    product = wc_api.get_product_by_id(product_id)
    # if product:
    #     wc_api.print_product_info(product)
    # print(json.dumps(product, indent=2))
    with open(f'product_data_{product_id}.json', 'w') as f:
        json.dump(product, f, indent=2)
    
if __name__ == "__main__":
    main()
