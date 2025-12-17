import requests
from typing import Dict, Optional, List, Union

class SalesforceWebToLeadService:
    # Constants based on your HTML Form
    ORG_ID = "00D58000000YppW"
    RET_URL = "https://yallaiot.com/"
    ENDPOINT = "https://webto.salesforce.com/servlet/servlet.WebToLead?encoding=UTF-8"

    # Custom Field Mappings (From your HTML)
    FIELD_PROJECT = "00NWS000006el81"
    FIELD_NOTES   = "00N4I00000EzMsn" # Used for "General Notes" or "Message"

    def __init__(self, org_id: str = None, debug_mode: bool = False, debug_email: str = None):
        """
        :param org_id: Optional override for Org ID.
        :param debug_mode: If True, tells Salesforce to send a debug email instead of creating a lead.
        :param debug_email: The email to receive debug logs.
        """
        self.org_id = org_id if org_id else self.ORG_ID
        self.debug_mode = debug_mode
        self.debug_email = debug_email

    def _submit(self, data: Dict) -> Dict:
        # Base payload required by Salesforce
        payload = {
            "oid": self.org_id,
            "retURL": self.RET_URL
        }
        
        # Add debug parameters if enabled
        if self.debug_mode:
            payload["debug"] = 1
            if self.debug_email:
                payload["debugEmail"] = self.debug_email

        # Merge specific form data
        payload.update(data)

        try:
            response = requests.post(self.ENDPOINT, data=payload)
            
            # Web-to-Lead usually returns 200 OK (and creates a redirect) even on some failures.
            # Real validation errors are only visible via email in Debug Mode.
            success = response.status_code == 200
            print('success:', success)
            
            return {
                "success": success,
                "status_code": response.status_code,
                "response_text": "Lead submitted (redirect)" if success else response.text
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


    # ======================================================================
    # 1. Contact Form (Directly maps to your HTML)
    # ======================================================================
    def insert_contact_form(self, first_name: str, last_name: str, email: str, mobile: str, company: str, country_code: str, project: Optional[str], general_notes: Optional[str]) -> Dict:
        
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile": mobile,         # HTML used 'mobile', standard API often uses 'phone'
            "company": company,
            "country_code": country_code, # e.g. 'AE', 'SA'
            self.FIELD_PROJECT: project,
            self.FIELD_NOTES: general_notes
        }

        return self._submit(payload)


    # ======================================================================
    # 2. Product Inquiries (Mapped to available Web-to-Lead fields)
    # ======================================================================
    def insert_product_inquiry(self, full_name: str, email: str, phone: str, company_name: str, project: Optional[str], message: Optional[str], products: List[str]) -> Dict:
        
        # Web-to-Lead expects first/last split. We try to split logic here.
        names = full_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else "-"

        # Combine products into the Project text area or Notes, as we lack a specific Product ID in the HTML provided
        product_str = ", ".join(products)
        project_details = f"{project} - Interested in: {product_str}" if project else f"Interested in: {product_str}"

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile": phone,
            "company": company_name,
            self.FIELD_PROJECT: project_details,
            self.FIELD_NOTES: message
            # Note: 'LeadSource' is not usually a standard hidden input in basic Web-to-Lead unless added as a custom field or hidden input.
            # You can add "lead_source": "Product Inquiry" if your SF configuration allows it via Web-to-Lead.
        }

        return self._submit(payload)


    # ======================================================================
    # 3. Sample Requests
    # ======================================================================
    def insert_sample_request(self, first_name: str, last_name: str, phone: str, email: str, company: str, project: Optional[str], quantity: Optional[str], product_id: Optional[str], message: Optional[str]) -> Dict:
        
        # We merge Quantity/Product ID into the Notes field because the HTML 
        # provided didn't have specific IDs for Quantity/Product ID.
        details = f"SAMPLE REQUEST. Qty: {quantity}, Product ID: {product_id}. \nMessage: {message}"

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile": phone,
            "company": company,
            self.FIELD_PROJECT: project,
            self.FIELD_NOTES: details
        }

        return self._submit(payload)

    # ======================================================================
    # 4. Shop Orders
    # ======================================================================
    def insert_shop_order(self, first_name: str, last_name: str, email: str, phone: str, country_code: str, city: str, product: Optional[str]) -> Dict:
        
        # Merging City/Product into notes as per available HTML fields
        order_details = f"SHOP ORDER. City: {city}. Product: {product}"

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile": phone,
            "company": "Online Shop Customer", 
            "country_code": country_code,
            self.FIELD_NOTES: order_details
        }

        return self._submit(payload)

