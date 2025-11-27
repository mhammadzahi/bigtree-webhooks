
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

product_enquiry_html = """
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <p>Hello,</p>

            <p>
            Please find your product spec sheet attached as requested.
            We will contact you soon with further details.
            </p>

            <p>Thank you!</p>
        </body>
    </html>
    """

single_product_html = """
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <p>Hello,</p>
            <p>
            Please find your requested product spec sheet attached.
            </p>

            <p>Thank you!</p>
        </body>
    </html>
    """

request_sample_html = """
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <p>Hello,</p>
            <p>
            Please find your requested product sample spec sheets attached.
            We will contact you soon with further details.
            </p>

            <p>Thank you!</p>
        </body>
    </html>
    """



def get_gmail_service():# Helper function
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


def create_message_without_attachments(to, subject, html_body):# Helper function
    message = MIMEMultipart("mixed")
    message["to"] = to
    message["from"] = FROM
    message["subject"] = subject
    # Create a "related" part for the HTML and potential embedded images
    related = MIMEMultipart("related")
    message.attach(related)

    html_part = MIMEText(html_body, "html")
    related.attach(html_part)
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}



def create_message_with_attachments(to, subject, html_body, pdf_files):# Herlper function
    message = MIMEMultipart("mixed")
    message["to"] = to
    message["from"] = FROM
    message["subject"] = subject
    # Create a "related" part for the HTML and potential embedded images
    related = MIMEMultipart("related")
    message.attach(related)

    html_part = MIMEText(html_body, "html")
    related.attach(html_part)

    # Attach each PDF file
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




def send_product_enquiry_email(to, pdf_files):
    service = get_gmail_service()
    body_message = create_message_with_attachments(to, "Product Enquiry", product_enquiry_html, pdf_files)
    
    try:
        message = service.users().messages().send(userId="me", body=body_message).execute()
        # print(f"Message Id: {message['id']}")
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False



def send_single_product_specsheet_email(to, file_path):
    service = get_gmail_service()
    body_message = create_message_with_attachments(to, "Product Specsheet", single_product_html, file_path)
    
    try:
        message = service.users().messages().send(userId="me", body=body_message).execute()
        # print(f"Message Id: {message['id']}")
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def send_request_sample_email(to, pdf_files):
    service = get_gmail_service()
    body_message = create_message_with_attachments(to, "Request Sample", request_sample_html, pdf_files)
    
    try:
        message = service.users().messages().send(userId="me", body=body_message).execute()
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def send_request_sample_to_admin(name):
    service = get_gmail_service()
    to = "sales@bigtree-group.com"
    body_message = create_message_without_attachments(to, "Request Sample from " + name, request_sample_admin_html)

    try:
        message = service.users().messages().send(userId="me", body=body_message).execute()
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False
