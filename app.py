from fastapi import FastAPI, Response, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, EmailStr, ValidationError
from functions.google_sheet_service import append_row
from functions.woocommerce_service import get_product, get_default_product_id
from functions.specsheet_generator import generate_specsheet_pdf
from functions.gmail_service import send_product_enquiry_email
import uvicorn, os, json

from dotenv import load_dotenv
load_dotenv()
SHEET_ID = os.getenv("SHEET_ID")
STORE_URL = os.getenv("WC_STORE_URL")
CUNSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CUNSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

app = FastAPI(title="BT Webhooks API", version="0.3.0", description="API for handling BigTree webhooks")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],  # Or ["POST"] if you want to be strict
    allow_headers=["*"],  # Or ["Content-Type"]
)


class ProductId(BaseModel):
    product_id: int


class EmailWebhook(BaseModel):
    Email: EmailStr


class ProductEnquiry(BaseModel):
    Email: EmailStr
    product_ids: list[int]




@app.post("/send-product-enquiry-email")
async def webhook_3(request: Request):
    payload = await request.json()
    # print(payload)
    try:
        validated_data = ProductEnquiry.model_validate(payload)
        product_ids = validated_data.product_ids
        email = validated_data.Email
        name = payload.get("name", "")

        product_default_ids = []
        for pid in product_ids:
            default_id = get_default_product_id(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=pid)
            if default_id:
                product_default_ids.append(default_id)


    except ValidationError as e:
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid Data"})

    row = [name, email, ", ".join(map(str, product_default_ids))]
    row_appended = append_row(SHEET_ID, "enquiries", row)

    pdf_specsheet_files = []
    for product_id in product_default_ids:
        product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)

        if not product:
            return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found"})

        file_path = generate_specsheet_pdf(product)    
        pdf_specsheet_files.append(file_path)

    if not send_product_enquiry_email(email, pdf_specsheet_files):
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to send enquiry email"})

    for file_path in pdf_specsheet_files:
        os.remove(file_path)

    # with open('1.json', 'w') as f:
    #    json.dump(product, f, indent=2)

    return JSONResponse(status_code=200, content={"status": "success"})



@app.post("/bt-product-specsheet")
async def webhook_2(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    try:
        validated_data = ProductId.model_validate(payload)
        product_id = validated_data.product_id

    except ValidationError as e:
        # print(f"Validation Error: {e}")
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing product_id field"})


    product = get_product(store_url=STORE_URL, consumer_key=CUNSUMER_KEY, consumer_secret=CUNSUMER_SECRET, product_id=product_id)

    if not product:
        return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found"})

    
    # with open(f'product_{product["id"]}_data.json', 'w') as f:
    #    json.dump(product, f, indent=2)


    file_path = generate_specsheet_pdf(product)
    background_tasks.add_task(os.remove, file_path)

    #return Response(status_code=status.HTTP_200_OK)
    response = FileResponse(path=file_path, media_type="application/pdf", filename=f"BigTree_{product['name']}_specsheet.pdf")
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    return response




@app.post("/bigtree-newsletter-email-webhook-v2-1-webhook")
async def webhook_1(request: Request):
    form_data = await request.form()
    # print(form_data)

    try:
        # 2. Validate the form data
        #    We convert the form_data to a dict and pass it to the model.
        #    This will check if "Email" exists AND if it's a valid email.
        validated_data = EmailWebhook.model_validate(dict(form_data))

        # 3. Get the validated email from the model
        email = validated_data.Email
        name = form_data.get("Name", "")

    except ValidationError as e:
        # If validation fails (missing field or bad email),
        # return a 422 Unprocessable Entity error.
        # print(f"Validation Error: {e}")
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing email field"})

    # print(f"Extracted email: {email}")

    row = [name, email]
    success = append_row(SHEET_ID, "subscribers", row)
    if not success:
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to append row to Google Sheet"})

    return Response(status_code=status.HTTP_200_OK)



@app.get("/")
async def root():
    return {"app": "BT", "version": "0.3.0", "status": "running"}

if __name__ == "__main__":
    # uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True) # Dev mode
    uvicorn.run(app, host="0.0.0.0", port=8001) # Prod mode
