from fastapi import FastAPI, Response, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, EmailStr, ValidationError
from functions.google_sheet_service import append_row
from functions.woocommerce_service import get_product
from functions.specsheet_generator import generate_specsheet_pdf
from functions.gmail import send_single_product_specsheet_email, send_product_enquiry_email, send_request_sample_email, send_request_sample_to_admin
import uvicorn, os, json
from typing import List

from dotenv import load_dotenv
load_dotenv()
SHEET_ID = os.getenv("SHEET_ID")
STORE_URL = os.getenv("WC_STORE_URL")
CUNSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CUNSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

app = FastAPI(title="BT Webhooks API", version="0.4.0", description="API for handling BigTree webhooks")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],  # Or ["POST"] if you want to be strict
    allow_headers=["*"],  # Or ["Content-Type"]
)

class EmailWebhook(BaseModel):# for newsletter subscription
    Email: EmailStr


class ProductIdAndEmail(BaseModel):# for single product specsheet
    product_id: int
    email: EmailStr


class CartItem(BaseModel):
    id: int
    quantity: int

class ProductEnquiry(BaseModel):# for multiple product enquiry (List)
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    project: str | None = None
    message: str | None = None
    cart_items: List[CartItem]



class RequestSample(BaseModel):
    product_ids: list[int]# for multiple product sample request (List)
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    project: str | None = None
    quantity: str
    message: str | None = None



@app.post("/bt-send-request-sample-webhook-v2-1")# need to change endpoint url
async def webhook_4(request: Request):
    payload = await request.json()
    print("-------- New Sample Request -------")
    print(payload)
    try:
        validated_data = RequestSample.model_validate(payload)

        product_ids = validated_data.product_ids
        first_name = validated_data.first_name
        last_name = validated_data.last_name
        email = validated_data.email
        phone = validated_data.phone
        company = validated_data.company
        project = validated_data.project
        quantity = validated_data.quantity
        message = validated_data.message


    except ValidationError as e:
        print(e)
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})

    row = [first_name, last_name, phone, company, email, message, project, quantity, ", ".join(map(str, product_ids))]
    row_appended = append_row(SHEET_ID, "sample_requests", row)

    # pdf_specsheet_files = []
    # for product_id in product_ids:
    #     product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)

    #     if not product:
    #         return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found"})

    #     file_path = generate_specsheet_pdf(product)    
    #     pdf_specsheet_files.append(file_path)

    # if not send_request_sample_email(email, pdf_specsheet_files):
    #     return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send sample request email"})

    if not send_request_sample_to_admin(first_name, last_name):
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send sample request email to admin"})

    # for file_path in pdf_specsheet_files:
    #     os.remove(file_path)

    return JSONResponse(status_code=200, content={"status": "success"})




@app.post("/bt-send-product-enquiry-webhook-v2-1")
async def webhook_3(request: Request):
    payload = await request.json()
    print(payload)
    try:
        validated_data = ProductEnquiry.model_validate(payload)
        first_name = validated_data.first_name
        last_name = validated_data.last_name
        email = validated_data.email
        phone = validated_data.phone
        company = validated_data.company
        project = validated_data.project
        message = validated_data.message
        cart_items = validated_data.cart_items
        product_ids = [item.id for item in cart_items]

    except ValidationError as e:
        print(e)
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})

    row = [first_name, last_name, email, phone, company, project, message, ", ".join(map(str, cart_items))]
    row_appended = append_row(SHEET_ID, "enquiries", row)

    pdf_specsheet_files = []
    for product_id in product_ids:
        product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)

        if not product:
            return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found"})

        file_path = generate_specsheet_pdf(product)    
        pdf_specsheet_files.append(file_path)

    if not send_product_enquiry_email(email, pdf_specsheet_files):
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send enquiry email"})

    for file_path in pdf_specsheet_files:
        os.remove(file_path)


    return JSONResponse(status_code=200, content={"status": "success"})



@app.post("/bt-single-product-specsheet-webhook-v2-1")
async def webhook_2(request: Request):
    payload = await request.json()
    # print(payload)

    try:
        validated_data = ProductIdAndEmail.model_validate(payload)
        product_id, email, name = validated_data.product_id, validated_data.email, payload.get("name", "")

    except ValidationError as e:
        # print(f"Validation Error: {e}")
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing fields"})


    product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)
    if not product:
        return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found"})

    row = [name, email, product_id]
    row_appended = append_row(SHEET_ID, "specsheets", row)

    # with open(f'product_{product["id"]}_data.json', 'w') as f:
    #    json.dump(product, f, indent=2)

    file_path = generate_specsheet_pdf(product)
    if not send_single_product_specsheet_email(email, file_path):
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send specsheet email"})

    os.remove(file_path)

    # response = FileResponse(path=file_path, media_type="application/pdf", filename=f"BigTree_{product['name']}_specsheet.pdf")
    # response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    # return response

    return JSONResponse(status_code=200, content={"status": "success"})




@app.post("/bigtree-newsletter-email-webhook-v2-1-webhook")
async def webhook_1(request: Request):
    form_data = await request.form()
    # print(form_data)

    try:
        validated_data = EmailWebhook.model_validate(dict(form_data))
        email = validated_data.Email
        name = form_data.get("Name", "")

    except ValidationError as e:
        # print(f"Validation Error: {e}")
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing email field"})

    # print(f"Extracted email: {email}")

    row = [name, email]
    success = append_row(SHEET_ID, "subscribers", row)
    if not success:
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to append row to Google Sheet"})

    return Response(status_code=status.HTTP_200_OK)



@app.get("/bigtree-webhooks-health-check")
async def root():
    return {"app": "BT", "version": "0.4.0", "status": "running"}

if __name__ == "__main__":
    # uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True) # Dev mode
    uvicorn.run(app, host="0.0.0.0", port=8001) # Prod mode
