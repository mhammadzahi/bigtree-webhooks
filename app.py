from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, EmailStr, ValidationError
from functions.append_row_sheet import append_row
from functions.product_api import get_product
import uvicorn, os

from dotenv import load_dotenv
load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = "Sheet1"


app = FastAPI()


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
        
    except ValidationError as e:
        # If validation fails (missing field or bad email),
        # return a 422 Unprocessable Entity error.
        print(f"Validation Error: {e}")
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing email field"})

    print(f"Extracted email: {email}")

    row = ["No Name", email, "Subscribed"]
    success = append_row(SHEET_ID, SHEET_NAME, row)
    if not success:
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to append row to Google Sheet"})

    return Response(status_code=status.HTTP_200_OK)



@app.post("/bt-product-specsheet")
async def webhook_2(request: Request):
    payload = await request.json()
    #print(f"Received payload: {payload}")

    try:
        validated_data = ProductId.model_validate(payload)
        product_id = validated_data.product_id

    except ValidationError as e:
        print(f"Validation Error: {e}")
        return JSONResponse(status_code=422, content={"status": "fail", "detail": "Invalid or missing product_id field"})


    product = get_product(
        store_url= os.getenv("WC_STORE_URL"),
        consumer_key=os.getenv("WC_CONSUMER_KEY"),
        consumer_secret=os.getenv("WC_CONSUMER_SECRET"),
        product_id=product_id
    )

    if not product::
        return JSONResponse(status_code=404, content={"status": "fail", "detail": "Product not found"})

    print(product)
    
    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
async def root():
    return {"app": "BT", "version": "1.2.2"}

if __name__ == "__main__":
    #uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True) # Dev mode
    uvicorn.run(app, host="0.0.0.0", port=8001) # Prod mode
