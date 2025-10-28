from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from functions.append_row_sheet import append_row
import uvicorn, os
from dotenv import load_dotenv


load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = "Sheet1"


app = FastAPI()


class EmailWebhook(BaseModel):
    email: EmailStr


@app.post("/bigtree-newsletter-email-webhook-v2-1-webhook")
async def webhook_1(payload: EmailWebhook):
    email = payload.email
    row = ["No Name", email, "Subscribed"]
    
    success = append_row(SHEET_ID, SHEET_NAME, row)
    if not success:
        return JSONResponse(status_code=500, content={"status": "fail", "detail": "Failed to append row to Google Sheet"})

    return JSONResponse(status_code=200)


@app.get("/")
async def root():
    return {"message": "Hello World, BT Newsletter Email Webhook is running!"}

if __name__ == "__main__":
    #uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True) # Dev mode
    uvicorn.run(app, host="0.0.0.0", port=8001) # Prod mode
