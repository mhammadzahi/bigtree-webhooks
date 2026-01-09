# BigTree Webhooks API

A robust FastAPI-based webhook service for BigTree Group's e-commerce operations, handling product inquiries, sample requests, specsheet generation, newsletter subscriptions, and contact form submissions with automated integration to Salesforce, Google Sheets, and Gmail.

## 🚀 Features

- **Product Specsheet Generation**: Dynamically generate and email PDF specification sheets for WooCommerce products
- **Product Enquiry Management**: Process multiple-product cart inquiries with PDF attachments
- **Sample Request Handling**: Manage sample requests with automatic lead creation in Salesforce
- **Contact Form Processing**: Capture and route contact submissions to Google Sheets and Salesforce
- **Newsletter Subscription**: Collect and store newsletter subscriptions
- **Email Automation**: Automated email delivery via Gmail API with customizable templates
- **Background Task Processing**: Asynchronous processing for improved response times
- **API Key Authentication**: Secure endpoints with API key validation

## 📋 Prerequisites

- Python 3.11 or higher
- WooCommerce store with API access
- Google Cloud Project with Gmail and Sheets API enabled
- Salesforce Web-to-Lead configuration
- Valid OAuth 2.0 credentials for Google services

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bigtree-webhooks
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Google Sheets
SHEET_ID=your_google_sheet_id

# WooCommerce
WC_STORE_URL=https://your-store.com
WC_CONSUMER_KEY=your_consumer_key
WC_CONSUMER_SECRET=your_consumer_secret

# API Security
API_KEY=your_secure_api_key
```

### 5. Set Up Google API Credentials

1. Place your `main-credentials.json` (OAuth 2.0 credentials) in the project root
2. Run the application once to generate `token.json` through the OAuth flow

## 🚦 Usage

### Development Mode

```bash
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

### Production Mode

```bash
python app.py
```

The API will be available at `http://0.0.0.0:8001`

## 📡 API Endpoints

### Health Check
```
GET /bigtree-webhooks-health-check
```
Returns application status and version information.

### Product Specsheet
```
POST /bt-single-product-specsheet-webhook-v2-1
Headers: X-API-Key: <your-api-key>
Body: {
  "product_id": 123,
  "email": "customer@example.com",
  "name": "Customer Name"
}
```
Generates and emails a product specification sheet PDF.

### Product Enquiry
```
POST /bt-send-product-enquiry-webhook-v2-1
Headers: X-API-Key: <your-api-key>
Body: {
  "name": "Customer Name",
  "email": "customer@example.com",
  "phone": "+1234567890",
  "company": "Company Inc",
  "project": "Project Name",
  "country": "Country",
  "message": "Optional message",
  "req_sample": "Yes",
  "cart_items": [
    {"id": 123, "quantity": 2},
    {"id": 456, "quantity": 1}
  ],
  "account_password": "optional_password"
}
```
Processes multiple-product inquiries with PDF specsheets.

### Sample Request
```
POST /bt-send-request-sample-webhook-v2-1
Headers: X-API-Key: <your-api-key>
Body: {
  "productId": [123, 456],
  "fname": "First",
  "lname": "Last",
  "email": "customer@example.com",
  "phone": "+1234567890",
  "company": "Company Inc",
  "project": "Project Name",
  "country": "Country",
  "qte": "100",
  "message": "Optional message",
  "account_password": "optional_password"
}
```
Handles product sample requests with Salesforce lead creation.

### Contact Form
```
POST /bt-contact-webhook-v2-1
Headers: X-API-Key: <your-api-key>
Body: {
  "fname": "First",
  "lname": "Last",
  "email": "customer@example.com",
  "phone": "+1234567890",
  "company": "Company Inc",
  "project": "Project Name",
  "project_location": "Location",
  "message": "Message content",
  "src": "website"
}
```
Processes contact form submissions.

### Newsletter Subscription
```
POST /bigtree-newsletter-email-webhook-v2-1-webhook
Content-Type: application/x-www-form-urlencoded
Body: Email=subscriber@example.com&Name=Subscriber Name
```
Registers newsletter subscriptions.

### Unsubscribe
```
GET /unsubscribe/{email_id}
```
Displays unsubscribe confirmation page.

## 📂 Project Structure

```
bigtree-webhooks/
├── app.py                          # Main FastAPI application
├── requirements.txt                # Python dependencies
├── .env                           # Environment configuration
├── main-credentials.json          # Google OAuth credentials
├── token.json                     # Generated OAuth token
├── modules/
│   ├── gmail_service.py           # Gmail API integration
│   ├── google_sheet_service.py    # Google Sheets API integration
│   ├── salesforce_service.py      # Salesforce Web-to-Lead service
│   ├── specsheet_generator.py     # PDF generation logic
│   └── woocommerce_service.py     # WooCommerce API client
├── email_templates/               # HTML email templates
│   ├── account_creation.html
│   ├── product_enquiry.html
│   ├── request_sample.html
│   ├── single_product_Specsheet.html
│   └── unsubscribe.html
└── files/
    └── temp/                      # Temporary PDF storage
```

## 🔧 Module Overview

### Gmail Service
- OAuth 2.0 authentication for Gmail API
- Email template loading and rendering
- Multi-attachment email support
- Automatic credential refresh

### Google Sheets Service
- Append data to specific sheets/tabs
- Track submissions with timestamps
- Organized data storage for different form types

### Salesforce Service
- Web-to-Lead integration
- Custom field mapping
- Debug mode for testing
- Contact and lead creation

### Specsheet Generator
- Dynamic PDF generation from WooCommerce product data
- Custom DOCX templates with InlineImage support
- HTML tag stripping and text formatting
- Multi-page layout with product images

### WooCommerce Service
- REST API integration
- Product data retrieval
- Image and metadata fetching

## 🔐 Security

- **API Key Authentication**: All webhook endpoints require a valid `X-API-Key` header
- **CORS Configuration**: Configurable origin restrictions
- **Input Validation**: Pydantic models for request validation
- **OAuth 2.0**: Secure Google API access with refresh tokens

## 🧪 Testing

To test endpoints locally, use tools like Postman or cURL:

```bash
curl -X POST http://127.0.0.1:8001/bigtree-webhooks-health-check
```

For authenticated endpoints:

```bash
curl -X POST http://127.0.0.1:8001/bt-single-product-specsheet-webhook-v2-1 \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"product_id": 123, "email": "test@example.com"}'
```

## 📝 Environment Configuration

Key environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `SHEET_ID` | Google Sheets document ID | Yes |
| `WC_STORE_URL` | WooCommerce store URL | Yes |
| `WC_CONSUMER_KEY` | WooCommerce API consumer key | Yes |
| `WC_CONSUMER_SECRET` | WooCommerce API consumer secret | Yes |
| `API_KEY` | Webhook authentication key | Yes |

## 🚀 Deployment

### Production Deployment Checklist

1. Set environment variables in production
2. Ensure `main-credentials.json` is securely stored
3. Configure firewall rules for port 8001
4. Set up process manager (e.g., systemd, supervisor)
5. Enable HTTPS with reverse proxy (nginx, Apache)
6. Configure logging and monitoring
7. Set up automatic restarts on failure

### Example systemd Service

```ini
[Unit]
Description=BigTree Webhooks API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/bigtree-webhooks
Environment="PATH=/path/to/bigtree-webhooks/env/bin"
ExecStart=/path/to/bigtree-webhooks/env/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📊 Data Flow

1. **Incoming Webhook** → API Key validation
2. **Request Validation** → Pydantic model validation
3. **Background Task** → Asynchronous processing
4. **External Services**:
   - Google Sheets: Data logging
   - Salesforce: Lead/contact creation
   - WooCommerce: Product data retrieval
   - Gmail: Email delivery
5. **Response** → Immediate 200 OK to client

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software owned by BigTree Group.

## 📧 Contact

BigTree Group - sales@bigtree-group.com

Project Link: [https://github.com/bigtree-group/bigtree-webhooks](https://github.com/bigtree-group/bigtree-webhooks)

---

**Version**: 1.1.0  
**Last Updated**: January 2026
