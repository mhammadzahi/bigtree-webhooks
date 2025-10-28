# BigTree Webhooks

A FastAPI application that handles email newsletter subscriptions and stores them in Google Sheets.

## Features

- Webhook endpoint for processing email subscriptions
- Integration with Google Sheets API
- Input validation using Pydantic
- Environment-based configuration
- Secure OAuth2 authentication for Google Sheets

## Prerequisites

- Python 3.8 or higher
- Google Cloud Console project with Sheets API enabled
- OAuth2 credentials file (`main-credentials.json`)

## Installation

1. Clone the repository:
```sh
git clone https://github.com/mhammadzahi/bigtree-webhooks.git
cd bigtree-webhooks
```

2. Install dependencies:
```sh
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your Google Sheet ID to the `.env` file:
```sh
SHEET_ID=your_sheet_id_here
```

4. Set up Google Sheets authentication:
   - Place your `main-credentials.json` file in the root directory
   - Run the application once to generate the `token.json` file

## Usage

Start the development server:

```sh
python app.py
```

Or use Uvicorn directly:

```sh
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

### API Endpoints

- `GET /`: Health check endpoint
- `POST /bigtree-newsletter-email-webhook-v2-1-webhook`: Subscribe email endpoint

### Example Request

```sh
curl -X POST "http://localhost:8001/bigtree-newsletter-email-webhook-v2-1-webhook" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}'
```

## Project Structure

```
bigtree-webhooks/
├── .env                    # Environment variables
├── app.py                 # Main FastAPI application
├── functions/
│   └── append_row_sheet.py # Google Sheets integration
├── requirements.txt       # Python dependencies
└── README.md             # Documentation
```

## Dependencies

- FastAPI: Web framework
- Google API Python Client: Google Sheets API integration
- Python-dotenv: Environment variable management
- Pydantic: Data validation
- Uvicorn: ASGI server

## License

This project is licensed under the MIT License - see the LICENSE file for details.
