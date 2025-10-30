from fastapi import FastAPI, Response, status, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, HttpUrl, ValidationError

from functions.append_row_sheet import append_row
from functions.generate_pdf import create_pdf_from_url

import uvicorn, os

from dotenv import load_dotenv
load_dotenv()


app = FastAPI()

#--------------------------------
import tempfile, logging
from starlette.responses import FileResponse


# Setup basic logging
logging.basicConfig(level=logging.INFO)


class URLRequest(BaseModel):
    url: HttpUrl

@app.post("/bigtree-download-pdf")
async def generate_pdf_endpoint(request: URLRequest):

    # Create a temporary file to store the PDF. This is a secure way to handle files.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        output_filename = temp_pdf.name
    
    # Run the PDF generation function
    success = create_pdf_from_url(str(request.url), output_filename)

    if not success or not os.path.exists(output_filename):
        # Clean up the temp file if it exists but generation failed
        if os.path.exists(output_filename):
            os.unlink(output_filename)
        raise HTTPException(status_code=500, detail="Failed to generate PDF from the provided URL.")

    # Create a clean filename for the user's download
    # e.g., 'https://example.com/my-page/' becomes 'my-page.pdf'
    download_filename = str(request.url.path).strip('/').split('/')[-1] or 'download'
    download_filename = f"{download_filename}.pdf"

    # Return the file as a response.
    # The file will be automatically deleted after the response is sent.
    return FileResponse(
        path=output_filename,
        media_type='application/pdf',
        filename=download_filename,
        background=BackgroundTask(os.unlink, output_filename) # Cleanup task
    )

#-------------------------------


class EmailWebhook(BaseModel):
    Email: EmailStr

SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = "Sheet1"

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



@app.get("/")
async def root():
    return {"message": "Hello World, BT Newsletter Email Webhook is running!"}

if __name__ == "__main__":
    #uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True) # Dev mode
    uvicorn.run(app, host="0.0.0.0", port=8001) # Prod mode