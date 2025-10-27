# Quick Start Workflow - Complete Integration Guide

## Overview

The Quick Start workflow enables field technicians and managers to rapidly create orders by entering a vehicle plate number as the primary identifier. The system then guides users through customer registration (if needed) and order creation, with optional document upload for automatic data extraction.

## Real-World Scenario

**Flow in Practice:**

```
1. Technician in field with vehicle (has plate: ABC-1234)
   ↓
2. Brings vehicle to workshop
   ↓
3. Manager clicks "Quick Start" button
   ↓
4. Modal: Enter plate "ABC-1234"
   ↓
5. System searches for existing vehicle/customer
   ↓
   a) Vehicle FOUND → Show existing customer info
      ↓
      Continue to Order Creation Form
   
   b) Vehicle NOT FOUND → Show "New Vehicle" message
      ↓
      Proceed to Customer Registration
      ↓
      Then Order Creation
   ↓
6. (Optional) Upload quotation document
   ↓
7. System extracts customer/order data
   ↓
8. Continue to normal form with pre-filled data
```

## System Components

### 1. **Quick Start Modal** (`partials/quick_start_modal.html`)

**Class**: `QuickStartFlow`

**Features:**
- Step 1: Enter vehicle plate (required, auto-search)
- Step 2: Display found vehicle/customer (if exists)
- Step 3: Show "new vehicle" confirmation (if not found)
- Step 4: Optional document upload for auto-fill
- Captures order start timestamp

**Key Methods:**
```javascript
searchVehicle()              // Search DB by plate
displayFoundVehicle()        // Show vehicle/customer details
uploadDocumentAndProceed()   // Upload & extract data
redirectToOrderFlow()        // Route to customer or order creation
```

**Data Flow:**
```
Vehicle Plate Input
  ↓
POST /api/documents/search-job-card/
  ↓
  Vehicle found?
  ├─ YES: Display vehicle/customer, offer continue
  └─ NO: Show new vehicle confirmation
  ↓
User clicks "Proceed"
  ↓
(Optional) Upload document
  POST /api/documents/upload/
  ↓
Redirect to:
  - Customer registration (if vehicle new) OR
  - Order creation (if customer exists)
```

### 2. **Customer Registration with Extraction** (`views_quick_start.py`)

**View**: `customer_register_with_extraction()`

**Handles:**
- Customer registration with pre-filled extracted data
- Links vehicle to customer
- Creates placeholder order if from quick start
- Accepts query params:
  - `vehicle_plate`: From quick start modal
  - `from_quick_start`: Flag to indicate flow origin
  - `extracted_document_id`: If document uploaded

**Flow:**
```
GET /customer/register-with-extraction/?vehicle_plate=ABC-1234&from_quick_start=true
  ↓
Display form with pre-filled data (if any)
  ↓
User submits
  ↓
Save customer
  ↓
Create vehicle linked to customer
  ↓
If from_quick_start:
  Create placeholder order
  ↓
  Redirect to Order Edit with extracted data
Else:
  Redirect to Customers List
```

**Pre-filled Fields:**
- `full_name`: From extracted document or manual entry
- `phone`: From extracted document
- `email`: From extracted document
- `address`: From extracted document
- `customer_type`: From extracted data or default to 'personal'

### 3. **Order Creation with Extraction** (`views_quick_start.py`)

**View**: `order_create_with_extraction()`

**Handles:**
- Pre-selects customer and vehicle
- Receives extracted data via query params or session
- Displays extraction data for review/editing
- Integrates with existing order creation flow

**Flow:**
```
GET /orders/create-with-extraction/?customer_id=5&vehicle_plate=ABC-1234
  ↓
Load customer & vehicle
  ↓
Fetch extracted data (if available)
  ↓
Display form with pre-filled order data
  ↓
User can:
  ├─ Accept suggested data
  ├─ Edit fields
  ├─ Handle data mismatches (if any)
  └─ Submit order
```

**Pre-filled Fields:**
- `description`: From extracted document description
- `item_name`: From extracted item name
- `brand`: From extracted brand
- `quantity`: From extracted quantity
- `tire_type`: From extracted tire type

### 4. **Auto-Fill and Merge APIs**

#### Auto-Fill Order from Extraction
```
POST /api/quick-start/auto-fill-order/

Body:
{
  "extraction_id": 123,
  "order_id": 456
}

Response:
{
  "success": true,
  "data": {
    "description": "...",
    "item_name": "...",
    "quantity": 4,
    ...
  }
}
```

#### Detect Customer Data Mismatches
```
POST /api/quick-start/detect-customer-mismatch/

Body:
{
  "customer_id": 5,
  "extracted_data": {
    "customer_name": "Ahmed Hassan",
    "customer_phone": "+966501234567",
    ...
  }
}

Response:
{
  "success": true,
  "has_mismatches": true,
  "mismatches": {
    "full_name": {
      "existing": "Ahmed H.",
      "extracted": "Ahmed Hassan"
    },
    ...
  }
}
```

#### Apply Customer Data Merge
```
POST /api/quick-start/apply-customer-merge/

Body:
{
  "customer_id": 5,
  "strategy": "merge" | "keep_existing" | "override",
  "merged_data": {
    "full_name": "Ahmed Hassan",
    "phone": "+966501234567"
  }
}

Response:
{
  "success": true,
  "customer_id": 5
}
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    QUICK START MODAL                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Step 1: Enter Plate → [ABC-1234]                           │
│  ↓                                                            │
│  POST /api/documents/search-job-card/                        │
│  ↓                                                            │
│  FOUND? ─ YES ──→ Step 2: Show Vehicle & Customer           │
│         └─ NO ──→ Step 3: Show "New Vehicle" Notice         │
│                                                               │
│  ↓ (User clicks "Continue")                                 │
│                                                               │
│  Step 4: (Optional) Upload Document                          │
│  POST /api/documents/upload/                                │
│  Returns: document_id, extracted_data                        │
│                                                               │
│  ↓ (User clicks "Proceed to Order")                         │
│                                                               │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ↓                     ↓
   CUSTOMER FOUND     VEHICLE NEW
        ↓                     ↓
   ┌────────────┐        ┌─────────────────┐
   │ Order      │        │ Customer        │
   │ Creation   │        │ Registration    │
   │ Form       │        │ Form            │
   │            │        │                 │
   │ Pre-filled │        │ Pre-filled with │
   │ customer & │        │ extracted data  │
   │ vehicle    │        │                 │
   └────────────┘        └────────┬────────┘
        ↓                         ↓
   Submit Order          Submit Customer
        ↓                         ↓
   Order Created          ┌──────────────┐
                          │ Placeholder  │
                          │ Order        │
                          │ Created      │
                          └──────┬───────┘
                                 ↓
                          Order Edit/Details
```

## URL Structure

### UI Entry Points

```
GET /
  → Click "Quick Start" button
  → Modal opens

GET /customer/register-with-extraction/?vehicle_plate=ABC-1234&from_quick_start=true
  → Customer registration form
  → Pre-filled from extracted data (if available)
  → Links to existing document (if uploaded)

GET /orders/create-with-extraction/?customer_id=5&vehicle_plate=ABC-1234
  → Order creation form
  → Customer & vehicle pre-selected
  → Extracted data available for review
```

### API Endpoints

```
POST /api/documents/search-job-card/
  Search for vehicle/customer by plate

POST /api/documents/upload/
  Upload & extract document data

POST /api/quick-start/auto-fill-order/
  Auto-fill order form from extraction

POST /api/quick-start/detect-customer-mismatch/
  Detect data conflicts between extracted & existing

POST /api/quick-start/apply-customer-merge/
  Apply merge strategy for conflicting data
```

## Session Storage

Quick start flow uses Django session to persist extracted data:

```python
request.session['extracted_order_data'] = {
    'customer_name': '...',
    'customer_phone': '...',
    'customer_email': '...',
    'customer_address': '...',
    'vehicle_make': '...',
    'vehicle_model': '...',
    'item_name': '...',
    'quantity': 4,
    'amount': '500.00',
    ...
}

request.session['extracted_document_id'] = 123
request.session['quick_start_time'] = '2024-01-15T10:30:00Z'
```

## Database Models Used

### DocumentScan
- Stores uploaded file
- Links to Order (optional)
- Tracks extraction status
- Indexes on vehicle_plate for quick search

### DocumentExtraction
- Stores extracted fields
- Linked to DocumentScan (one-to-one)
- Contains extracted_data_json for flexible storage
- Confidence score (0-100%)

### Order
- `started_at`: Captured from quick start time
- `vehicle`: FK to Vehicle (optional but linked in quick start)
- `customer`: FK to Customer (required)
- Links to DocumentScan via document_scans relation

### Vehicle
- `plate_number`: Primary identifier (indexed)
- `customer`: FK to Customer
- `make`, `model`, `vehicle_type`: From extracted data or manual entry

### Customer
- `full_name`: From extracted data or registration
- `phone`: From extracted data or manual entry
- `email`: From extracted data
- `address`: From extracted data or manual entry

## Data Mismatch Resolution

When extracted data conflicts with existing customer data:

**Option 1: Keep Existing**
- Discard extracted data
- Use current database values

**Option 2: Override with Extracted**
- Replace all fields with extracted values
- Faster for bulk updates

**Option 3: Merge with Manual Review**
- User selects per-field which data to keep
- Best for careful data management

## Integration Points

### Customer Registration Form
- Must accept `vehicle_plate` query param
- Must accept `from_quick_start` flag
- Should populate initial form data from extracted_order_data session
- Should link created customer to vehicle from quick start

### Order Creation Form
- Must accept `customer_id` and `vehicle_plate` query params
- Should pre-select customer & vehicle
- Should display extracted data for review
- Should have "Quick Auto-Fill" button for document data
- Should warn about data mismatches

### Order List/Detail Pages
- Add "Upload Document" button in order list
- Allows adding documents to existing orders
- Documents linked via DocumentScan model

### Customer List/Detail Pages
- Add "Quick Start Order" button in customer detail
- Pre-fills customer in quick start modal
- Allows starting order directly from customer view

## Configuration & Settings

### File Upload Settings
```python
# settings.py
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
```

### Time Zone
```python
TIME_ZONE = 'Asia/Riyadh'
USE_TZ = True
```

### Session Configuration
```python
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
```

## Error Handling

### Validation Errors
- Vehicle plate format validation (on client & server)
- Customer field validation (email, phone format)
- Order field validation (quantity, amount)

### File Upload Errors
- File type validation (PDF, JPEG, PNG, BMP, TIFF)
- File size validation (max 50MB)
- Virus/malware scanning (optional)

### Data Extraction Errors
- OCR failures (fallback to manual entry)
- Pattern matching failures (partial data extracted)
- Confidence scoring (low confidence = review recommended)

### Mismatch Handling
- Automatic detection of conflicting fields
- User-guided resolution strategies
- Audit trail of merge decisions

## Performance Considerations

### Database Queries
- Index on `vehicle.plate_number` for quick searches
- Index on `customer.phone` for phone-based matching
- Index on `documentscan.vehicle_plate` for doc searches

### Caching
- Cache extracted data briefly (5 min) to avoid re-extraction
- Cache vehicle search results (1 min) during quick start flow
- Pre-load customer suggestions during registration

### File Processing
- Limit PDF extraction to first 10 pages
- Compress uploaded images before processing
- Async extraction for large documents (future enhancement)

## Testing Checklist

- [ ] Vehicle plate search (existing vehicle found)
- [ ] Vehicle plate search (new vehicle not found)
- [ ] Customer registration with pre-filled data
- [ ] Order creation with pre-selected customer
- [ ] Document upload with data extraction
- [ ] Data mismatch detection and resolution
- [ ] Order created with correct start time
- [ ] Vehicle linked to customer
- [ ] Extracted data pre-fills forms correctly
- [ ] Session data persists across page navigations
- [ ] File upload and virus scanning works
- [ ] OCR extracts text from images
- [ ] PDF extraction works for various PDF formats

## Troubleshooting

### Vehicle Not Found in Search
- Check if plate number is stored correctly in Vehicle model
- Verify indexing on `plate_number` field
- Check if vehicle is in correct branch (if multi-tenant)

### Extracted Data Not Showing
- Verify document extraction completed (check `extraction_status`)
- Check document file is readable and not corrupted
- Verify extraction confidence score (low = poor quality)

### Customer Registration Form Not Pre-Filled
- Check if `extracted_order_data` is in session
- Verify session backend is configured (db or cache)
- Check JavaScript is not clearing session storage

### Order Not Linked to Document
- Verify DocumentScan has order_id set correctly
- Check foreign key constraint on Order
- Verify document upload success response

## Future Enhancements

1. **Async Processing**
   - Queue document extraction for large files
   - Send notification when complete

2. **Machine Learning**
   - Custom NER model for customer names
   - Auto-detect customer type from document
   - Improve field matching accuracy

3. **Mobile Support**
   - Mobile-optimized quick start modal
   - Camera capture for document photos
   - Offline mode for vehicle search

4. **Integration**
   - Export to accounting software
   - Integrate with payment systems
   - SMS/Email notifications

5. **Analytics**
   - Track quick start usage metrics
   - Average order creation time
   - Data extraction accuracy statistics

## Support & Documentation

For detailed component documentation, see:
- `DOCUMENT_EXTRACTION_GUIDE.md` - Document extraction system
- `tracker/templates/tracker/partials/quick_start_modal.html` - Modal component
- `tracker/views_quick_start.py` - View logic and APIs
- `tracker/static/js/document_handler.js` - JavaScript utilities

## Related Files

- `tracker/templates/tracker/partials/quick_start_modal.html` (506 lines)
- `tracker/views_quick_start.py` (322 lines)
- `tracker/utils/document_extraction.py` (458 lines)
- `tracker/templates/tracker/partials/document_capture_modal.html` (573 lines)
- `tracker/static/js/document_handler.js` (411 lines)

## Summary

The Quick Start workflow provides:

✅ **Speed** - Enter plate → get order in 2-3 steps
✅ **Intelligence** - Auto-detect existing customers/vehicles
✅ **Flexibility** - Works for new and existing customers
✅ **Automation** - Extract data from documents automatically
✅ **Control** - User can review and approve all data
✅ **Audit** - Complete tracking of merge decisions and timestamps
