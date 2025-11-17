
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# --- Configuration ---
SENDER_EMAIL = "your_email@gmail.com"
RECIPIENT_EMAIL = "recipient_email@example.com"
EMAIL_SUBJECT = "HTML Email with 3 PDF Attachments"

# List of PDF files to attach
PDF_ATTACHMENTS = ["document1.pdf", "document2.pdf", "document3.pdf"]

# --- Gmail API Setup ---
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def create_message_with_attachments(sender, to, subject, html_content, files):
    """Creates a MIME multipart message with an HTML body and attachments."""
    message = MIMEMultipart("mixed")
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject

    # Create a "related" part for the HTML and potential embedded images
    related = MIMEMultipart("related")
    message.attach(related)

    # Attach the HTML body
    html_part = MIMEText(html_content, "html")
    related.attach(html_part)

    # Attach each PDF file
    for file_path in files:
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

def send_product_enquiry_email(message):
    service = get_gmail_service()
    try:
        message = service.users().messages().send(userId="me", body=message).execute()
        print(f"Message Id: {message['id']}")
        return message
    except Exception as e:
        print(f"An error occurred: {e}")
        return None



if __name__ == "__main__":

    html_body = """
    <html>
    <body>
        <h1>Hello,</h1>
        <p>This is an email with an HTML body and <strong>three PDF attachments</strong>.</p>
        <p>Please find the attached documents for your review.</p>
        <p>Thank you!</p>
    </body>
    </html>
    """

    # Create the email message
    email_message = create_message_with_attachments(SENDER_EMAIL, RECIPIENT_EMAIL, EMAIL_SUBJECT, html_body, PDF_ATTACHMENTS)

    send_product_enquiry_email(email_message)
