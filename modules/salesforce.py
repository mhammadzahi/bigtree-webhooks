from simple_salesforce import Salesforce
from typing import Dict, Optional, List


class SalesforceLeadService:
    def __init__(self, username: str, password: str, security_token: str):
        self.sf = Salesforce(username=username, password=password, security_token=security_token)

    # ======================================================================
    # 1. Product Inquiries
    # ======================================================================
    def insert_product_inquiry(self, full_name: str, email: str, phone: str, company_name: str, project: Optional[str], message: Optional[str], sample_request: Optional[str], products: List[str], timestamp: str) -> Dict:

        payload = {
            "LastName": full_name,                       # Full name stored in LastName if no split
            "Email": email,
            "Phone": phone,
            "Company": company_name,
            "Project__c": project,
            "Message__c": message,
            "Sample_Request__c": sample_request,
            "Products__c": ",".join(products),
            "Timestamp__c": timestamp,
            "LeadSource": "Product Inquiry"
        }

        return self.sf.Lead.create(payload)

    # ======================================================================
    # 2. Sample Requests
    # ======================================================================
    def insert_sample_request(self, first_name: str, last_name: str, phone: str, email: str, company: str, project: Optional[str], quantity: Optional[str], product_id: Optional[str], message: Optional[str], timestamp: str) -> Dict:

        payload = {
            "FirstName": first_name,
            "LastName": last_name,
            "Email": email,
            "Phone": phone,
            "Company": company,
            "Project__c": project,
            "Quantity__c": quantity,
            "Product_ID__c": product_id,
            "Message__c": message,
            "Timestamp__c": timestamp,
            "LeadSource": "Sample Request"
        }

        return self.sf.Lead.create(payload)

    # ======================================================================
    # 3. Contact Form
    # ======================================================================
    def insert_contact_form(self, first_name: str, last_name: str, email: str, phone: str, company: str, location: Optional[str], project: Optional[str], message: Optional[str], timestamp: str) -> Dict:

        payload = {
            "FirstName": first_name,
            "LastName": last_name,
            "Email": email,
            "Phone": phone,
            "Company": company,
            "Location__c": location,
            "Project__c": project,
            "Message__c": message,
            "Timestamp__c": timestamp,
            "LeadSource": "Contact Form"
        }

        return self.sf.Lead.create(payload)

    # ======================================================================
    # 4. Shop Orders
    # ======================================================================
    def insert_shop_order(self, first_name: str, last_name: str, email: str, phone: str, country: str, street_address: str, timestamp: str, city: str, product: Optional[str]) -> Dict:

        payload = {
            "FirstName": first_name,
            "LastName": last_name,
            "Email": email,
            "Phone": phone,
            "Company": "Online Shop",             # Required Salesforce field
            "Country__c": country,
            "Street_Address__c": street_address,
            "Timestamp__c": timestamp,
            "City__c": city,
            "Product__c": product,
            "LeadSource": "Online Shop Order"
        }

        return self.sf.Lead.create(payload)




'''
Notes:
    1. You must create these Salesforce custom fields: 

    Project__c
    Message__c
    Sample_Request__c
    Products__c
    Timestamp__c
    Quantity__c
    Product_ID__c
    Location__c
    Country__c
    Street_Address__c
    City__c
    Product__c
'''


# ==========================================================================
# Example usage
# ==========================================================================
if __name__ == "__main__":
    sf_service = SalesforceLeadService(username="YOUR_USERNAME", password="YOUR_PASSWORD", security_token="YOUR_SECURITY_TOKEN")

    # Example: Product inquiry
    result = sf_service.insert_product_inquiry(
        full_name="John Doe",
        email="john@example.com",
        phone="+123456789",
        company_name="ABC Corp",
        project="Villa Project",
        message="I need pricing.",
        sample_request="Yes",
        products=["5340", "4698", "5818"],
        timestamp="2025-12-12 14:00:00"
    )

    print(result)
