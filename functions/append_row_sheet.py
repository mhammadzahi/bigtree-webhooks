import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CLIENT_SECRETS_FILE = "main-credentials.json"
TOKEN_FILE = "token.json"

def init_sheets_service():
    try:
        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        # If no valid credentials, start OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for next run
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        service = build("sheets", "v4", credentials=creds)
        return service

    except Exception as e:
        print(f"An error occurred during sheet service initialization: {e}")
        return None


def append_row(sheet_id: str, sheet_name: str, row_data: list) -> bool:
    try:
        if not isinstance(row_data, list):
            raise ValueError("row_data must be a list")

        service = init_sheets_service()
        if not service:
            print("Sheet service not available.")
            return False

        range_name = f"{sheet_name}!A1"
        value_range_body = {"values": [row_data]}

        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=value_range_body
            ).execute()
        )

        updated_rows = result.get("updates", {}).get("updatedRows", 0)
        # print(f"{updated_rows} rows appended.")
        return True

    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return False

    except ValueError as e:
        print(f"A value error occurred: {e}")
        return False

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

