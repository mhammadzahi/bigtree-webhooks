from fastapi import FastAPI, Response, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, EmailStr, ValidationError
from modules.specsheet_generator import generate_specsheet_pdf
from modules.google_sheet_service import append_row
from modules.woocommerce_service import get_product
from modules.salesforce import SalesforceWebToLeadService
from modules.gmail_service import send_single_product_specsheet_email, send_product_enquiry_email, send_request_sample_email, send_account_creation_email
import uvicorn, os, json, asyncio
from typing import List
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()
SHEET_ID = os.getenv("SHEET_ID")
STORE_URL = os.getenv("WC_STORE_URL")
CUNSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CUNSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

SALES_EMAIL = "sales@bigtree-group.com"
API_KEY = os.getenv("API_KEY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend domain
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],  # Or ["Content-Type"]
)

sf = SalesforceWebToLeadService(debug_mode=True, debug_email="mzahi@bigtree-group.com")






class ContactRequest(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    phone: str
    company: str
    project: str
    project_location: str
    message: str | None = None
    src: str | None = None

@app.post("/bt-contact-webhook-v2-1")#5. Contact Request -- done -- [contact page]
async def contact_request_webhook(request: Request):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "fail", "detail": "Unauthorized"})
    
    payload = await request.json()
    try:
        validated_data = ContactRequest.model_validate(payload)
        fname = validated_data.fname
        lname = validated_data.lname
        email = validated_data.email
        phone = validated_data.phone
        company = validated_data.company
        project = validated_data.project
        project_location = validated_data.project_location
        message = validated_data.message
        src = validated_data.src

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})

    row = [fname, lname, email, phone, company, project, project_location, message, src, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
    row_appended = append_row(SHEET_ID, "contact", row)

    result = sf.insert_contact_form(first_name=fname, last_name=lname, email=email, mobile=phone, company=company, country_code=project_location, project=project, general_notes=message)
    # print("Salesforce Response:", result)

    # if not send_product_enquiry_ _admin(name, email): # or send to salesforce
    #     return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send contact request email to admin"})

    return JSONResponse(status_code=200, content={"status": "success"})


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


@app.post("/bt-send-request-sample-webhook-v2-1")#4. Request Sample -- ??? -- [single product page] 
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

    row = [first_name, last_name, phone, email, company, project, country, quantity, ", ".join(map(str, product_ids)), message, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
    row_appended = append_row(SHEET_ID, "sample_requests", row)
    
    # Combine product_ids and message into other_product_interest field
    other_product_interest = f"Product IDs: {', '.join([str(pid) for pid in product_ids])}. Message: {message}"
    result = sf.insert_sample_request(first_name=first_name, last_name=last_name, email=email, company=company, mobile=phone, project=project, country=country, quantity=quantity, other_product_interest=other_product_interest)

    async def fetch_and_generate(product_id):
        try:
            product = await asyncio.to_thread(get_product, store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)
            if not product:
                return None
            file_path = await asyncio.to_thread(generate_specsheet_pdf, product, wc_url=STORE_URL, wc_key=CUNSUMER_KEY, wc_secret=CUNSUMER_SECRET)
            return file_path
        except Exception as e:
            print(f"Error generating PDF for product {product_id}: {e}")
            return None
    
    results = await asyncio.gather(*[fetch_and_generate(pid) for pid in product_ids])
    
    if None in results:
        return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found or PDF generation failed"})
    
    pdf_specsheet_files = results

    # if not send_request_sample_email(email, pdf_specsheet_files, cc=SALES_EMAIL):
    #     return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send sample request email"})

    # if account_password:
    #     if not send_account_creation_email(email, account_password):
    #         return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send account creation email"})

    for file_path in pdf_specsheet_files:
        background_tasks.add_task(os.remove, file_path)

    return JSONResponse(status_code=200, content={"status": "success"})



class CartItem(BaseModel):
    id: int
    quantity: int

class ProductEnquiry(BaseModel):
    name: str
    email: EmailStr
    phone: str
    company: str
    project: str
    country: str
    message: str | None = None
    req_sample: str
    cart_items: List[CartItem]
    account_password: str | None = None

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
        country = validated_data.country
        message = validated_data.message
        account_password = validated_data.account_password
        req_sample = validated_data.req_sample # Yes/No
        cart_items = validated_data.cart_items
        product_ids = [item.id for item in cart_items]

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})

    row = [name, email, phone, company, project, country, message, req_sample, ", ".join(map(str, cart_items)), datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
    row_appended = append_row(SHEET_ID, "enquiries", row)

    # Merge req_sample into message
    combined_message = f"Sample Request: {req_sample}. {message}" if message else f"Sample Request: {req_sample}" 
    result = sf.insert_product_inquiry(full_name=name, email=email, phone=phone, company_name=company, project=project, country=country, message=combined_message, products=[str(pid) for pid in product_ids])

    async def fetch_and_generate(product_id):
        try:
            product = await asyncio.to_thread(get_product, store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)
            if not product:
                return None
            file_path = await asyncio.to_thread(generate_specsheet_pdf, product, wc_url=STORE_URL, wc_key=CUNSUMER_KEY, wc_secret=CUNSUMER_SECRET)
            return file_path
        except Exception as e:
            print(f"Error generating PDF for product {product_id}: {e}")
            return None
    
    results = await asyncio.gather(*[fetch_and_generate(pid) for pid in product_ids])
    
    # Filter out None values (failed PDFs) and only use successfully generated ones
    pdf_specsheet_files = [f for f in results if f is not None]
    
    if not pdf_specsheet_files:
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to generate any PDFs"})

    if not send_product_enquiry_email(name, email, pdf_specsheet_files, cc=SALES_EMAIL):
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send enquiry email"})


    # if account_password: # if created account
    #     if not send_account_creation_email(email, account_password):
    #         return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send account creation email"})

    for file_path in pdf_specsheet_files:
        background_tasks.add_task(os.remove, file_path)

    return JSONResponse(status_code=200, content={"status": "success"})



class SpecSheetWebhook(BaseModel):
    product_id: int
    email: EmailStr

@app.post("/bt-single-product-specsheet-webhook-v2-1")#2. Product Specsheet [single product page] --done--
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

    row = [name, email, product_id, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
    row_appended = append_row(SHEET_ID, "specsheets", row)

    file_path = generate_specsheet_pdf(product, wc_url=STORE_URL, wc_key=CUNSUMER_KEY, wc_secret=CUNSUMER_SECRET)
    if not send_single_product_specsheet_email(email, file_path):
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send specsheet email"})

    background_tasks.add_task(os.remove, file_path)
    
    response = FileResponse(path=file_path, media_type="application/pdf", filename=f"BigTree_{product['name']}_specsheet.pdf")
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    return response


class NewsletterWebhook(BaseModel):
    Email: EmailStr

@app.post("/bigtree-newsletter-email-webhook-v2-1-webhook")#1. Newsletter -- done -- [footer]
async def newsletter_webhook(request: Request):
    # api_key = request.headers.get("X-API-Key")
    # if not api_key or api_key != API_KEY:
    #     return JSONResponse(status_code=422, content={"status": "fail", "detail": "Unauthorized"})
    
    form_data = await request.form()
    try:
        validated_data = NewsletterWebhook.model_validate(dict(form_data))
        email = validated_data.Email
        name = form_data.get("Name", "")

    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing email field"})

    row = [name, email, datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")]
    success = append_row(SHEET_ID, "subscribers", row)
    if not success:
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to append row to Google Sheet"})

    return Response(status_code=status.HTTP_200_OK)



@app.get("/unsubscribe/{email_id}")
async def unsubscribe(email_id: str, request: Request):
    with open("email_templates/unsubscribe.html", "r") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content, status_code=200)


@app.get("/bigtree-webhooks-health-check")
async def health_check():
    return {"app": "BT", "version": "0.4.1", "status": "running"}


if __name__ == "__main__":
    # uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True) # Dev mode
    uvicorn.run(app, host="0.0.0.0", port=8001) # Prod mode

