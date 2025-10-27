# Document Extraction & Management System

## Overview

This system enables users to capture vehicle information and upload documents (quotations, invoices, receipts, etc.) with automatic data extraction using AI/ML and Python libraries. The system can identify existing records and handle data merging intelligently.

## System Architecture

### Components

#### 1. **Frontend Components**

##### Document Capture Modal (`partials/document_capture_modal.html`)
- **Location**: `tracker/templates/tracker/partials/document_capture_modal.html`
- **Features**:
  - Tab-based interface (Vehicle Info → Upload Document → Extracted Data)
  - Vehicle plate capture (required)
  - Document type selection (Quotation, Invoice, Receipt, Estimate, Other)
  - Drag & drop file upload support
  - Real-time extraction preview
  - Confidence score display
  - Existing record detection

##### Data Mismatch Handler (`partials/data_mismatch_handler.html`)
- **Location**: `tracker/templates/tracker/partials/data_mismatch_handler.html`
- **Features**:
  - Visual comparison of existing vs extracted data
  - Three resolution strategies:
    - Keep Existing Data
    - Override with Extracted Data
    - Merge with Manual Review

##### Document Handler JavaScript (`static/js/document_handler.js`)
- **Location**: `tracker/static/js/document_handler.js`
- **Class**: `DocumentHandler`
- **Methods**:
  - `uploadAndExtract()` - Upload and extract data
  - `searchByJobCard()` - Search existing records
  - `createOrderFromDocument()` - Create order from extracted data
  - `detectMismatches()` - Compare extracted vs existing data
  - `resolveMismatches()` - Resolve data conflicts
  - `updateTableWithData()` - Update tables dynamically
  - `autoLinkRecords()` - Link documents to existing records

#### 2. **Backend Components**

##### Document Models (`tracker/models.py`)
```python
class DocumentScan(models.Model):
    """Stores uploaded documents with extraction status"""
    - order (FK to Order)
    - vehicle_plate (indexed)
    - customer_phone (indexed)
    - file (FileField)
    - document_type (choices: quotation, invoice, receipt, estimate, other)
    - extraction_status (choices: pending, processing, completed, failed)

class DocumentExtraction(models.Model):
    """Stores extracted data from documents"""
    - document (OneToOne to DocumentScan)
    - extracted_customer_name, phone, email, address
    - extracted_vehicle_plate, make, model, type
    - extracted_order_description, service_type
    - extracted_item_name, brand, quantity, tire_type, amount
    - confidence_overall (0-100)
    - extracted_data_json (flexible storage)
```

##### Document Extraction Utility (`tracker/utils/document_extraction.py`)
- **Class**: `DocumentExtractor`
- **Supports**:
  - PDF extraction (PyMuPDF preferred, fallback to PyPDF2)
  - Image extraction (PIL + pytesseract OCR)
  - Pattern-based data extraction (phone, email, plate, amounts)
  - Confidence scoring
  - Record matching

##### Document Views (`tracker/views_documents.py`)
- `upload_document()` - Handle file upload and extraction
- `get_document_extraction()` - Retrieve extraction data
- `create_order_from_document()` - Create order from extracted data
- `verify_and_update_extraction()` - Update extracted data
- `search_by_job_card()` - Search for existing records
- `start_quick_order()` - Create placeholder order with job card

## Data Flow

### 1. Document Upload Flow

```
User Opens Modal
    ↓
Enters Vehicle Plate (required)
    ↓
Selects Document Type
    ↓
Uploads Document (PDF/Image)
    ↓
System Extracts Text
    ↓
Pattern Matching for:
    - Phone numbers
    - Email addresses
    - Vehicle plates
    - Currency amounts
    - Service keywords
    ↓
Search Existing Records
    (by plate or phone)
    ↓
Display Extracted Data
    ↓
Show Confidence Score
    ↓
User Reviews & Creates Order
```

### 2. Data Mismatch Resolution

```
Document Uploaded
    ↓
Extracted Data vs Existing Data
    ↓
Mismatches Detected?
    ↓
Yes → Show Mismatch Modal
    ↓
User Selects Strategy:
    - Keep Existing
    - Override with Extracted
    - Merge Manually
    ↓
Apply Resolution
    ↓
Create Order with Resolved Data
```

### 3. Existing Record Detection & Auto-Linking

```
Extract Vehicle Plate from Document
    ↓
Search Database for Plate
    ↓
Found? → Get Customer & Recent Orders
    ↓
Extract Phone from Document
    ↓
Cross-reference with Customer
    ↓
Suggest Auto-Linking (if confidence high)
    ↓
User Can Accept or Manual Link
```

## Supported File Types

### PDF Files
- **Tool**: PyMuPDF (fitz) - Primary
- **Fallback**: PyPDF2
- **Features**: 
  - Text extraction from first 10 pages
  - Fast processing
  - Handles modern PDFs well

### Image Files
- **Extensions**: .jpg, .jpeg, .png, .bmp, .tiff
- **Tool**: pytesseract (Tesseract OCR)
- **Features**:
  - Automatic image preprocessing
  - Upscaling for small images
  - Grayscale conversion for clarity
  - Handles scanned documents

### File Size Limit
- **Max**: 50MB per document

## Extracted Data Fields

### Customer Information
- Full Name
- Phone Number
- Email Address
- Address

### Vehicle Information
- Plate Number (main identifier)
- Make/Brand
- Model
- Vehicle Type

### Service/Order Information
- Service Type (from keywords)
- Item Name
- Brand
- Quantity
- Tire Type
- Amount/Price

### Metadata
- Raw Text (first 10,000 characters)
- Confidence Score (0-100%)
- Extraction Timestamp
- Document Source Type (PDF/OCR)

## Extraction Patterns

### Regex Patterns Used

```python
PATTERNS = {
    'phone': r'(?:\+\d{1,3}[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{4}',
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'plate': r'[A-Z]{2,3}[-\s]?\d{2,4}[-\s]?[A-Z]{2,3}|\d{2,4}[-\s]?[A-Z]{2,4}',
    'currency_amount': r'(?:\$|SAR|AED|KWD|QAR|OMR|BHD)?\s*[\d,]+\.?\d*',
    'vehicle_make': r'\b(Toyota|Honda|Ford|BMW|...|Suzuki)\b'
}
```

## Confidence Scoring

Calculated based on found fields (0-100%):
- Phone numbers found: +20%
- Email addresses found: +20%
- Vehicle plates found: +30%
- Vehicle makes found: +15%
- Currency amounts found: +15%

**Low Confidence** (<40%): Review carefully before creating order
**Medium Confidence** (40-70%): Some data requires verification
**High Confidence** (>70%): Data ready for use

## Database Schema

### DocumentScan Table
```
id | order_id | vehicle_plate | customer_phone | file | document_type
extracted_status | extraction_error | extracted_at | uploaded_at | uploaded_by
```

### DocumentExtraction Table
```
id | document_id | raw_text | extracted_customer_name | extracted_customer_phone
extracted_vehicle_plate | extracted_vehicle_make | extracted_quantity | extracted_amount
confidence_overall | extracted_data_json | extracted_at | updated_at
```

## API Endpoints

### Document Upload
```
POST /api/documents/upload/
- Body: FormData with file, vehicle_plate, document_type
- Response: { document_id, extraction_id, extracted_data, matches, confidence }
```

### Get Extraction
```
GET /api/documents/{doc_id}/extraction/
- Response: { document, extraction details }
```

### Create Order
```
POST /api/documents/create-order/
- Body: { extraction_id, vehicle_plate, customer_phone, ... }
- Response: { order_id, order_number, customer_id, vehicle_id }
```

### Verify Extraction
```
POST /api/documents/verify-extraction/
- Body: { extraction_id, corrected fields }
- Response: { success, message }
```

### Search Records
```
POST /api/documents/search-job-card/
- Body: { job_card_number, vehicle_plate }
- Response: { found, results with order/customer/vehicle }
```

### Quick Start Order
```
POST /api/orders/quick-start/
- Body: { job_card_number, vehicle_plate }
- Response: { order_id, order_number, job_card_number }
```

## UI Integration

### Sidebar Button
- **Location**: Main sidebar under "Pinned" section
- **Label**: "Upload Document"
- **Icon**: File icon
- **Action**: Opens document capture modal

### Header Button
- **Location**: Top right navigation bar
- **Label**: "Upload Doc" (responsive, hidden on mobile)
- **Icon**: Cloud upload icon
- **Action**: Opens document capture modal

### Modal Tabs
1. **Vehicle Info Tab**
   - Vehicle plate input (required)
   - Make/Model/Type (optional)
   - Preview of captured data

2. **Upload Document Tab**
   - Document type selector
   - Drag & drop upload area
   - File selection
   - Customer phone (optional)

3. **Extracted Data Tab**
   - Customer information preview
   - Vehicle information preview
   - Service information preview
   - Confidence score
   - Existing records found
   - Create order button

## Configuration

### Settings in `settings.py`
```python
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
# Max upload: 50MB (set in view)
# Timeout: 25 seconds (APScheduler)
```

### Environment Variables
```
DEBUG = True/False
DB_PATH = ./db.sqlite3 (or MySQL config)
TIMEZONE = Asia/Riyadh
```

## Dependencies

### Python Libraries
- **PyMuPDF** (fitz) - PDF text extraction
- **PyPDF2** - PDF fallback
- **pytesseract** - OCR for images
- **Pillow** - Image processing
- **numpy** - Image preprocessing
- **Django** - Web framework
- **sqlite3/MySQL** - Database

### JavaScript
- **Bootstrap 5** - UI components & modals
- **jQuery** - DOM manipulation
- **Fetch API** - AJAX requests

## Error Handling

### Upload Errors
- File type not supported
- File size exceeds limit
- Upload timeout

### Extraction Errors
- OCR not installed (pytesseract)
- PDF library not available
- Text extraction failed
- Pattern matching errors

### Data Errors
- Customer/vehicle not found
- Order creation failed
- Data validation errors

## Performance Considerations

### Optimization Tips
1. **Limit PDF pages**: First 10 pages extracted (adjustable)
2. **Image preprocessing**: Only on small images (<400px)
3. **Database indexes**: On vehicle_plate, customer_phone
4. **Caching**: Extraction results cached briefly
5. **Async processing**: Consider Celery for large files

### Throughput
- Small files (<5MB): <2 seconds
- Medium files (5-20MB): 5-10 seconds
- Large files (20-50MB): 15-30 seconds

## Testing

### Test Cases
1. **PDF extraction**: Various PDF formats
2. **Image extraction**: JPEG, PNG, BMP, TIFF
3. **Data matching**: Phone and plate matching
4. **Mismatch handling**: All three strategies
5. **Order creation**: With and without conflicts
6. **Table updates**: Dynamic row addition/update

### Sample Test File Locations
```
/test_documents/
  ├── sample_quotation.pdf
  ├── sample_invoice.pdf
  ├── scanned_document.jpg
  └── test_data.json
```

## Security Considerations

### File Upload Security
- File type validation (MIME type)
- File size limits (50MB)
- Virus scanning (optional)
- Secure filename generation

### Data Security
- CSRF protection on all forms
- User authentication required
- Branch scoping (multi-tenant)
- Audit logging

### OCR Security
- Local processing (no external APIs)
- No data sent to third parties
- Results stored in database

## Troubleshooting

### "PyMuPDF not installed"
```bash
pip install PyMuPDF
# or
pip install -r requirements.txt
```

### "pytesseract not found"
```bash
pip install pytesseract
# Also install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki
```

### OCR Poor Quality
- Ensure image quality is good
- Try preprocessing in image editor
- Check Tesseract configuration
- Try alternative PDF tool (PyMuPDF)

### Extraction Not Working
- Check file format (PDF/JPEG/PNG)
- Verify file size (<50MB)
- Check extraction status in database
- Review debug logs

## Future Enhancements

1. **Machine Learning**
   - Named entity recognition (NER)
   - Custom training for domain-specific docs
   - Confidence scoring improvements

2. **Advanced Features**
   - Batch document upload
   - Scheduled extraction jobs
   - Document versioning
   - Extraction history

3. **Integration**
   - Azure Form Recognizer
   - Google Document AI
   - AWS Textract

4. **UX Improvements**
   - Drag & drop batch upload
   - Real-time preview
   - Extraction progress bar
   - Suggested corrections

## API Reference

Full API documentation available in inline comments in:
- `tracker/views_documents.py`
- `tracker/utils/document_extraction.py`
- `tracker/static/js/document_handler.js`

## Support

For issues or questions:
1. Check debug.log in project root
2. Review model definitions in models.py
3. Test with sample documents
4. Check browser console for JavaScript errors
5. Verify file permissions on media folder

## Version History

- **v1.0** (Current)
  - Initial release
  - PDF & image extraction
  - Auto-linking and mismatch handling
  - Django integration
  - Modal UI implementation
