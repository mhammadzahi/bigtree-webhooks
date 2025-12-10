
import base64, os, mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


main_creds = "main-credentials.json"
token_file = "token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/spreadsheets"]
FROM = "BigTree Group <web@bigtree-group.com>"

def load_email_template(template_name):
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "email_templates", template_name)
    with open(template_path, "r") as file:
        return file.read()

def get_gmail_service():
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(main_creds, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)



def create_message(to, subject, html_body, pdf_files=None, attachments=False):
    message = MIMEMultipart("mixed")
    message["to"] = to
    message["from"] = FROM
    message["subject"] = subject
    message["cc"] = "sales@bigtree-group.com"
    related = MIMEMultipart("related")
    message.attach(related)

    html_part = MIMEText(html_body, "html")
    related.attach(html_part)

    # Attach each PDF file if attachments are enabled
    if attachments and pdf_files:
        for file_path in pdf_files:
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"
            main_type, sub_type = content_type.split("/", 1)

            with open(file_path, "rb") as fp:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(fp.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=os.path.basename(file_path))
                message.attach(part)

    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}



def send_product_enquiry_email(full_name, password=None, to, pdf_files):
    service = get_gmail_service()
    html_body = load_email_template("product_enquiry.html")
    body_message = create_message(to, "Product Enquiry", html_body, pdf_files, attachments=True)
    
    try:
        message = service.users().messages().send(userId="me", body=body_message).execute()
        return True

    except Exception as e:
        print(f"An error occurred in [send_product_enquiry_email]: {e}")
        return False



def send_single_product_specsheet_email(to, file_path):
    service = get_gmail_service()
    html_body = load_email_template("single_product.html")
    body_message = create_message(to, "Product Specsheet", html_body, [file_path], attachments=True)
    try:
        message = service.users().messages().send(userId="me", body=body_message).execute()
        return True

    except Exception as e:
        print(f"An error occurred in [send_single_ product_ specsheet_email]: {e}")
        return False


def send_request_sample_email(to, pdf_files):
    service = get_gmail_service()
    body_message = create_message(to, "Request Sample", request_sample_html, pdf_files, attachments=True)
    
    try:
        message = service.users().messages().send(userId="me", body=body_message).execute()
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


