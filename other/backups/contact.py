import requests

def send_lead_to_salesforce(lead_data):
    # 1. The Salesforce Endpoint (from the <form action="...">)
    url = "https://webto.salesforce.com/servlet/servlet.WebToLead?encoding=UTF-8"

    # 2. Prepare the payload
    # We combine the user data with the required hidden fields (oid, retURL)
    payload = {
        'oid': '00D58000000YppW',  # Your Organization ID
        'retURL': 'https://yallaiot.com/contact-us/',
        
        # Standard Fields
        'first_name': lead_data.get('first_name'),
        'last_name': lead_data.get('last_name'),
        'email': lead_data.get('email'),
        'mobile': lead_data.get('mobile'),
        'company': lead_data.get('company'),
        'country_code': lead_data.get('country_code'), # e.g., 'AE', 'SA', 'BH'
        
        # Custom Fields (specific to your Salesforce setup)
        '00NWS000006el81': lead_data.get('project_description'), # Project
        '00N4I00000EzMsn': lead_data.get('general_notes'),       # General Notes
        
        # Optional: Uncomment these to debug if leads aren't appearing
        # 'debug': 1,
        # 'debugEmail': 'your_email@example.com' 
    }

    try:
        # 3. Send the POST request
        response = requests.post(url, data=payload)

        # 4. Check results
        # Salesforce Web-to-Lead usually returns 200 OK even if it fails validation,
        # unless 'debug=1' is set. It typically redirects to the retURL.
        if response.status_code == 200:
            print("Successfully submitted lead to Salesforce.")
        else:
            print(f"Failed to submit. Status Code: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")

# --- Usage Example ---
if __name__ == "__main__":
    # This is the data you want to send (e.g., from your own database or API)
    new_lead = {
        'first_name': 'Ahmed',
        'last_name': 'Al-Mansoori',
        'email': 'ahmed.test@yallaiot.com',
        'mobile': '+971509999999',
        'company': 'Tech Innovation LLC',
        'country_code': 'AE', # United Arab Emirates
        'project_description': 'Looking for 500 GPS trackers.',
        'general_notes': 'Please send a quote via email first.'
    }

    send_lead_to_salesforce(new_lead)



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
