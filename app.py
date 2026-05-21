from fastapi import FastAPI, Response, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, EmailStr, ValidationError
from typing import List

from modules.specsheet_generator import generate_specsheet_pdf
from modules.google_sheet_service import append_row
from modules.woocommerce_service import get_product
from modules.salesforce_service import SalesforceWebToLeadService
from modules import gmail_service

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import uvicorn, os, json


load_dotenv()
SHEET_ID = os.getenv("SHEET_ID")
STORE_URL = os.getenv("WC_STORE_URL")
CUNSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CUNSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

SALES_EMAIL = os.getenv("SALES_EMAIL")
DEVELOPER_EMAIL = os.getenv("DEVELOPER_EMAIL")

API_KEY = os.getenv("API_KEY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend domain
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],  # Or ["Content-Type"]
)

sf = SalesforceWebToLeadService(debug_mode=True, debug_email=DEVELOPER_EMAIL)


class SupplierRequest(BaseModel):
    fname: str
    lname: str
    company: str
    country: str
    email: EmailStr
    message: str | None = None
    phone: str
    products: list[str]
    website: str

def process_supplier_request(company, country, email, fname, lname, message, phone, products, website):
    try:
        # 1. Append to Google Sheet
        products_str = ", ".join(products) if products else ""
        row = [fname, lname, company, email, phone, products_str, website, country, message, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
        append_row(SHEET_ID, "Supplier", row)

        # 2. Send email
        gmail_service.send_welcome_supplier_email(email, f"{fname} {lname}", SALES_EMAIL)

    except Exception as e:
        print(f"Error processing supplier request for {email}: {e}")

@app.post("/bt-supplier-webhook-v2-1")
async def supplier_webhook(request: Request, background_tasks: BackgroundTasks):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "fail", "detail": "Unauthorized"})
    
    payload = await request.json()
    # print("SUPPLIER PAYLOAD: \n", json.dumps(payload, indent=2))

    try:
        validated_data = SupplierRequest.model_validate(payload)
        fname = validated_data.fname
        lname = validated_data.lname
        company = validated_data.company
        country = validated_data.country
        email = validated_data.email
        message = validated_data.message
        phone = validated_data.phone
        products = validated_data.products
        website = validated_data.website
        
    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})
    
    background_tasks.add_task(process_supplier_request, company, country, email, fname, lname, message, phone, products, website)
    return JSONResponse(status_code=200, content={"status": "success", "message": "Processing your request"})



class ContactRequest(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    phone: str
    company: str
    role: str
    project: str
    project_location: str
    message: str | None = None
    src: str | None = None

def process_contact_request(fname, lname, email, phone, company, role, project, project_location, message, src):
    try:
        row = [fname, lname, email, phone, company, role, project, project_location, message, src, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
        append_row(SHEET_ID, "Contact", row)
        
        sf_result = sf.insert_contact_form(first_name=fname, last_name=lname, email=email, mobile=phone, company=company, role=role, country_code=project_location, project=project, general_notes=message)
        print('sf_result: ', sf_result)

    except Exception as e:
        print(f"Error processing contact request for {email}: {e}")

@app.post("/bt-contact-webhook-v2-1")#5. Contact Request -- done -- [contact page]
async def contact_request_webhook(request: Request, background_tasks: BackgroundTasks):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "fail", "detail": "Unauthorized"})
    
    payload = await request.json()
    # print("PAYLOAD: \n", json.dumps(payload, indent=2))
    try:
        validated_data = ContactRequest.model_validate(payload)
        fname = validated_data.fname
        lname = validated_data.lname
        email = validated_data.email
        phone = validated_data.phone
        company = validated_data.company
        role = validated_data.role
        project = validated_data.project
        project_location = validated_data.project_location
        message = validated_data.message
        src = validated_data.src

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})


    background_tasks.add_task(process_contact_request, fname, lname, email, phone, company, role, project, project_location, message, src)
    return JSONResponse(status_code=200, content={"status": "success", "message": "Processing your request"})



class RequestSample(BaseModel):
    productId: list[int]
    fname: str
    lname: str
    email: EmailStr
    account_password: str | None = None
    phone: str
    company: str
    project: str
    country: str
    qte: str
    message: str | None = None

async def process_request_sample(first_name, last_name, email, phone, company, project, country, quantity, message, product_ids, account_password):
    try:
        # 1. Append to Google Sheet
        row = [first_name, last_name, phone, email, company, project, country, quantity, ", ".join(map(str, product_ids)), message, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
        append_row(SHEET_ID, "Sample Request", row)
        
        # 2. Insert into Salesforce
        other_product_interest = f"Product IDs: {', '.join([str(pid) for pid in product_ids])}. Message: {message}"
        sf_result = sf.insert_sample_request(first_name=first_name, last_name=last_name, email=email, company=company, mobile=phone, project=project, country=country, quantity=quantity, other_product_interest=other_product_interest)
        # print("Salesforce Response:", sf_result)

        # 3. Generate PDFs
        pdf_specsheet_files = []
        for product_id in product_ids:
            product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)
            if product:
                file_path = await generate_specsheet_pdf(product, wc_url=STORE_URL, wc_key=CUNSUMER_KEY, wc_secret=CUNSUMER_SECRET)
                pdf_specsheet_files.append(file_path)

        # 4. Send request sample email
        if pdf_specsheet_files:
            gmail_service.send_request_sample_email(email, pdf_specsheet_files, cc=SALES_EMAIL)

        # 5. Send account creation email if password provided
        if account_password:
            gmail_service.send_account_creation_email(email, account_password)

        # 6. Clean up generated PDF files
        for file_path in pdf_specsheet_files:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to remove file {file_path}: {e}")

    except Exception as e:
        print(f"Error processing sample request for {email}: {e}")

@app.post("/bt-send-request-sample-webhook-v2-1")#4. Request Sample --  -- [single product page] 
async def request_sample_webhook(request: Request, background_tasks: BackgroundTasks):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "fail", "detail": "Unauthorized"})
    
    payload = await request.json()
    try:
        validated_data = RequestSample.model_validate(payload)
        product_ids = validated_data.productId
        first_name = validated_data.fname
        last_name = validated_data.lname
        email = validated_data.email
        account_password = validated_data.account_password
        phone = validated_data.phone
        company = validated_data.company
        project = validated_data.project
        country = validated_data.country
        quantity = validated_data.qte
        message = validated_data.message

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})

    background_tasks.add_task(process_request_sample, first_name, last_name, email, phone, company, project, country, quantity, message, product_ids, account_password)
    return JSONResponse(status_code=200, content={"status": "success", "message": "Processing your request"})



class CartItem(BaseModel):
    id: int
    quantity: int

class ProductEnquiry(BaseModel):
    name: str
    email: EmailStr
    phone: str
    company: str
    project: str
    project_type: str | None = None
    country: str
    message: str | None = None
    req_sample: str
    cart_items: List[CartItem]
    account_password: str | None = None

async def process_enquiry(name, email, phone, company, project, project_type, country, message, req_sample, cart_items, product_ids, account_password):
    try:
        # 1. Append to Google Sheet
        row = [name, email, phone, company, project, project_type or '', country, message, req_sample, ", ".join(map(str, cart_items)), datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
        append_row(SHEET_ID, "Inquiries", row)

        # 2. Insert into Salesforce
        combined_message = f"Sample Request: {req_sample}. {message}" if message else f"Sample Request: {req_sample}"
        sf_result = sf.insert_product_inquiry(full_name=name, email=email, phone=phone, company_name=company, project=project, project_type=project_type, country=country, message=combined_message, products=[str(pid) for pid in product_ids])

        # 3. Generate PDFs
        pdf_specsheet_files = []
        for product_id in product_ids:
            product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)
            if product:
                file_path = await generate_specsheet_pdf(product, wc_url=STORE_URL, wc_key=CUNSUMER_KEY, wc_secret=CUNSUMER_SECRET)
                pdf_specsheet_files.append(file_path)

        # 4. Send enquiry email
        if pdf_specsheet_files:
            gmail_service.send_product_enquiry_email(name, email, pdf_specsheet_files, cc=SALES_EMAIL)

        # 5. Send account creation email if password provided
        if account_password:
            gmail_service.send_account_creation_email(email, account_password)

        # 6. Clean up generated PDF files
        for file_path in pdf_specsheet_files:
            try:
                os.remove(file_path)

            except Exception as e:
                print(f"Failed to remove file {file_path}: {e}")

    except Exception as e:
        print(f"Error processing product enquiry for {email}: {e}")

@app.post("/bt-send-product-enquiry-webhook-v2-1")#3. Product Enquiry -- Done -- [multiple products in cart]
async def product_enquiry_webhook(request: Request, background_tasks: BackgroundTasks):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "fail", "detail": "Unauthorized"})

    payload = await request.json()
    try:
        validated_data = ProductEnquiry.model_validate(payload)
        name = validated_data.name
        email = validated_data.email
        phone = validated_data.phone
        company = validated_data.company
        project = validated_data.project
        project_type = validated_data.project_type
        country = validated_data.country
        message = validated_data.message
        account_password = validated_data.account_password
        req_sample = validated_data.req_sample # Yes/No
        cart_items = validated_data.cart_items
        product_ids = [item.id for item in cart_items]

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})

    background_tasks.add_task(process_enquiry, name, email, phone, company, project, project_type, country, message, req_sample, cart_items, product_ids, account_password)
    return JSONResponse(status_code=200, content={"status": "success", "message": "Processing your request"})



class SpecSheetWebhook(BaseModel):
    product_id: int
    email: EmailStr

def process_specsheet(name, email, product_id, file_path):
    try:
        row = [name, email, product_id, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
        append_row(SHEET_ID, "Specsheet Download", row)
        # gmail_service.send_single_product_specsheet_email(email, file_path)
        try:
            os.remove(file_path)

        except Exception as e:
            print(f"Failed to remove file. {e}")

    except Exception as e:
        print(f"Error processing specsheet. {e}")

@app.post("/bt-single-product-specsheet-webhook-v2-1")#2. Product Specsheet [single product page]
async def specsheet_webhook(request: Request, background_tasks: BackgroundTasks):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "fail", "detail": "Unauthorized"})
    
    payload = await request.json()
    try:
        validated_data = SpecSheetWebhook.model_validate(payload)
        product_id, email, name = validated_data.product_id, validated_data.email, payload.get("name", "")

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing fields"})


    product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)
    if not product:
        return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found"})

    file_path = await generate_specsheet_pdf(product, wc_url=STORE_URL, wc_key=CUNSUMER_KEY, wc_secret=CUNSUMER_SECRET)
    background_tasks.add_task(process_specsheet, name, email, product_id, file_path)

    response = FileResponse(path=file_path, media_type="application/pdf", filename=f"BigTree_{product['name']}_specsheet.pdf")
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    return response



class NewsletterWebhook(BaseModel):
    Email: EmailStr

def process_newsletter(name, email):
    try:
        row = [name, email, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
        append_row(SHEET_ID, "Subscribers", row)

    except Exception as e:
        print(f"Error processing newsletter subscription for {email}: {e}")

@app.post("/bigtree-newsletter-email-webhook-v2-1-webhook")
async def newsletter_webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    try:
        validated_data = NewsletterWebhook.model_validate(dict(form_data))
        email = validated_data.Email
        name = form_data.get('Name', '')

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing email field"})

    background_tasks.add_task(process_newsletter, name, email)
    return Response(status_code=status.HTTP_200_OK)



def process_unsubscribe(email_id):
    email_id = email_id.replace("email=", "")
    try:
        with open("unsubscribed_emails.txt", "a") as f:
            f.write(f"{email_id}\n")

    except Exception as e:
        print(f"Error processing unsubscribe for {email_id}: {e}")


@app.get("/unsubscribe/{email_id}")
async def unsubscribe(email_id: str, request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_unsubscribe, email_id)
    with open("email_templates/unsubscribe.html", "r") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content, status_code=200)


@app.get("/bigtree-webhooks-health-check")
async def health_check():
    return {"App": "BT Webhooks", "Version": "3.3.4", "Status": "running"}


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8001
    # uvicorn.run("app:app", host=host, port=port, reload=True) # Dev
    uvicorn.run(app, host=host, port=port) # Prod
