# Invoice Extraction System - Complete Setup & Usage Guide

This document provides step-by-step instructions to set up and use the new invoice scanning/extraction system.

## What's New

The system now includes:

1. **Quick Start Order** - Create orders with just a vehicle plate number
2. **Template-based Invoice Extraction** - Auto-extract customer, vehicle, and service data from invoices
3. **Started Orders Dashboard** - View all initiated orders by plate number
4. **Service Templates** - Common services with estimated durations
5. **Invoice Pattern Matching** - Regex-based field extraction for flexibility

---

## Setup Instructions

### Step 1: Run Migrations

After pulling the changes, run:

```bash
python manage.py migrate tracker
```

This creates the following new database tables:
- `ServiceTemplate` - Store common services with estimation times
- `InvoicePatternMatcher` - Define regex patterns for field extraction

### Step 2: Seed Default Data

Run the management command to populate default service templates and extraction patterns:

```bash
python manage.py seed_service_templates
```

This creates:
- 8 common service templates (Oil Change, Tire Rotation, Brake Service, etc.)
- 8 invoice pattern matchers for extracting common fields

You can modify these later via Django admin.

### Step 3: Verify Admin Interface

Log in to Django admin (`/admin/`) and check:

1. **Tracker > Service Templates**
   - Browse existing service templates
   - Add new services with keywords and estimated minutes

2. **Tracker > Invoice Pattern Matchers**
   - View all regex patterns for field extraction
   - Modify patterns based on your invoice formats
   - Adjust priority and enable/disable patterns

### Step 4: Optional - Install OCR (for image invoices)

For OCR capability to extract text from invoice images:

```bash
pip install pytesseract pillow
```

You also need Tesseract binary installed on your system:

- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

---

## User Workflow

### Creating a New Order

1. **On Dashboard**
   - Click the purple "Quick Start Order" banner button
   - Enter vehicle plate number (e.g., "ABC 123 XYZ")
   - Select order type: Service, Sales, or Inquiry
   - Click "Start Order"

2. **Order Created**
   - System creates order with status "New"
   - Redirects to order detail page
   - Plate number becomes unique identifier

### Uploading Invoice to Extract Data

1. **On Order Detail Page**
   - Click "Upload Invoice/Document" button
   - Select document type (Invoice, Quotation, Receipt, etc.)
   - Upload file (PNG, JPG, or PDF)
   - System automatically extracts data

2. **Review Extracted Data**
   - Go to "Documents" tab
   - View extracted fields:
     - Customer name, phone, email
     - Vehicle plate number
     - Service description
     - Quantities and amounts
   - Click "Apply to Order" to populate fields

### Manual Data Entry

1. Click "Customer Info" button to edit:
   - Name, phone, email
   - Address
   - Customer type (Personal, Company, Government, NGO)

2. Click "Vehicle Info" button to edit:
   - Make and model
   - Vehicle type

3. System saves all changes automatically

### Completing the Order

When all details are filled:
- Click "Complete Order" button
- Order status changes to "Completed"
- Can no longer edit the order

---

## Started Orders Dashboard

View all initiated orders that haven't been completed:

**Features:**
- Filter by search (plate number or customer name)
- Sort by newest first, oldest first, plate number, or type
- See KPI cards: orders started today, total pending, unique vehicles
- Group orders by plate number for easy navigation
- Click any order to continue editing

**URL:** `/orders/started/`

---

## Service Templates Configuration

Service templates are used to:

1. Match extracted service descriptions from invoices
2. Auto-assign estimated service duration
3. Help organize services by type (Service/Sales/Both)

### Adding a New Service Template

1. Go to Django Admin → Tracker → Service Templates
2. Click "Add Service Template"
3. Fill in:
   - **Name**: Service name (e.g., "Complete Engine Overhaul")
   - **Keywords**: Comma-separated keywords (e.g., "engine, overhaul, complete, rebuild")
   - **Estimated Minutes**: How long the service takes
   - **Service Type**: Service, Sales, or Both
   - **Is Common**: Check if frequently used
   - **Is Active**: Check to enable

4. Save

**Tips:**
- Use descriptive keywords that appear in your invoices
- Order keywords from most specific to most general
- Set realistic duration estimates for your business

---

## Invoice Pattern Configuration

Patterns define how to extract fields from invoice text using regex.

### Common Fields

- `plate_number` - Vehicle plate/license number
- `customer_name` - Customer name
- `customer_phone` - Customer phone number
- `customer_email` - Customer email
- `service_description` - What service/item is being sold
- `quantity` - Quantity of items
- `amount` - Total monetary amount

### Customizing Patterns

1. Go to Django Admin → Tracker → Invoice Pattern Matchers
2. Click a pattern to edit
3. Modify the regex pattern to match your invoice format

**Example:**

If your invoices show amounts like "Total: Tsh 50,000.00", create pattern:

- **Field Type**: amount
- **Regex Pattern**: `Total[\s:]*([0-9,]+\.\d{2})`
- **Extract Group**: 1
- **Priority**: 10 (lower = higher priority)

### Testing Patterns

Use regex testers online (e.g., regex101.com) to test patterns against your invoice text.

---

## API Endpoints

### Start Order

```
POST /api/orders/start/
Content-Type: application/json

{
  "plate_number": "ABC 123 XYZ",
  "order_type": "service"  // or "sales", "inquiry"
}

Response:
{
  "success": true,
  "order_id": 123,
  "order_number": "ORD20240115120000XXXX",
  "plate_number": "ABC 123 XYZ",
  "started_at": "2024-01-15T12:00:00Z"
}
```

### Apply Extraction to Order

```
POST /api/orders/apply-extraction/
Content-Type: application/json

{
  "order_id": 123,
  "extraction_id": 456,
  "apply_fields": ["customer_name", "customer_phone", "service_description"]
}

Response:
{
  "success": true,
  "message": "Extraction data applied to order successfully",
  "order_id": 123
}
```

### Auto-Fill from Latest Extraction

```
POST /api/orders/auto-fill-extraction/
Content-Type: application/json

{
  "order_id": 123
}

Response:
{
  "success": true,
  "data": {
    "customer_name": "John Doe",
    "customer_phone": "+255123456789",
    "service_description": "Oil Change",
    "estimated_minutes": 30,
    ...
  },
  "extraction_id": 456,
  "confidence": 80
}
```

---

## File Structure

New/Modified files:

```
tracker/
├── models.py                          # Added ServiceTemplate, InvoicePatternMatcher
├─�� extraction_utils.py                # Invoice extraction logic
├── views_start_order.py               # Order start and dashboard views
├── admin.py                           # Admin UI for templates
├── urls.py                            # New URL routes
├── migrations/
│   └── 0001_add_service_templates...  # Migration for new models
├── management/commands/
│   └── seed_service_templates.py      # Populate default data
├── templates/tracker/
│   ├── started_orders_dashboard.html  # Dashboard of all started orders
│   ├── started_order_detail.html      # Detail view for single order
│   └── partials/
│       └── start_order_modal.html     # Start order modal
```

---

## Troubleshooting

### Migration fails

**Issue**: "No changes detected in app tracker"

**Solution**: Check that `tracker/migrations/__init__.py` exists and migration file is in the correct location.

### Extraction shows no data

**Possible causes**:
1. Invoice format doesn't match any patterns
2. Regex patterns need adjustment
3. OCR not installed (if using image uploads)

**Solution**:
1. Check extracted raw text in database
2. Test patterns with invoice samples
3. Adjust regex patterns in admin

### Service template not matching

**Issue**: Extracted service description doesn't match any template

**Solution**:
1. Edit template and add more keywords
2. Use comma-separated variations
3. Order keywords from specific to general

---

## Performance Notes

- Pattern matching uses regex (fast)
- Service matching uses keyword lookup (very fast)
- OCR processing (if enabled) may take 5-10 seconds per image
- Extraction results are cached in DocumentExtraction records

---

## Future Enhancements

Potential improvements:
- Machine learning-based service matching
- Multi-language support for OCR
- Custom field definitions per branch
- Integration with accounting systems
- Batch invoice processing
- Manual invoice correction UI

---

## Support

For issues or questions:
1. Check Django error logs: `tail -f logs/django.log`
2. Review database records: Admin panel
3. Test patterns locally: regex101.com
4. Check extraction raw text in DocumentExtraction model
