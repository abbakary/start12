"""
Async extraction utilities using threading to handle background document processing.
This provides asynchronous extraction without requiring Celery.
"""

import threading
import logging
from django.core.cache import cache
from tracker.extraction_utils import process_invoice_extraction
from tracker.models import DocumentScan, DocumentExtraction, DocumentExtractionItem

logger = logging.getLogger(__name__)


def start_extraction_task(document_scan_id):
    """
    Start an extraction task in background thread.
    
    Args:
        document_scan_id: ID of DocumentScan to extract
    """
    thread = threading.Thread(
        target=_extract_document_worker,
        args=(document_scan_id,),
        daemon=True
    )
    thread.start()


def _extract_document_worker(document_scan_id):
    """
    Worker function that runs in a background thread.
    Extracts document and updates DocumentScan/DocumentExtraction records.
    
    Args:
        document_scan_id: ID of DocumentScan to extract
    """
    try:
        doc_scan = DocumentScan.objects.get(id=document_scan_id)
        
        # Update status to processing
        doc_scan.extraction_status = 'processing'
        doc_scan.save(update_fields=['extraction_status'])
        
        # Cache extraction status
        _set_extraction_progress(document_scan_id, 'processing', 10, '')
        
        # Run extraction
        try:
            extracted_data = process_invoice_extraction(doc_scan)
            
            if 'error' not in extracted_data:
                _set_extraction_progress(document_scan_id, 'processing', 50, 'Extraction successful, saving data...')
                
                # Persist extraction record
                from decimal import Decimal, InvalidOperation
                
                def _to_decimal_safe(v):
                    try:
                        if v is None:
                            return None
                        if isinstance(v, (int, float, Decimal)):
                            return Decimal(str(v))
                        s = str(v).replace(',', '').strip()
                        return Decimal(s)
                    except (InvalidOperation, Exception):
                        return None

                extraction = DocumentExtraction.objects.create(
                    document=doc_scan,
                    extracted_customer_name=extracted_data.get('customer_name') or extracted_data.get('extracted_customer_name'),
                    extracted_customer_phone=extracted_data.get('customer_phone') or extracted_data.get('extracted_customer_phone'),
                    extracted_customer_email=extracted_data.get('customer_email') or extracted_data.get('extracted_customer_email'),
                    extracted_vehicle_plate=extracted_data.get('plate_number') or extracted_data.get('extracted_vehicle_plate'),
                    extracted_order_description=extracted_data.get('service_description') or extracted_data.get('extracted_order_description'),
                    extracted_item_name=extracted_data.get('item_name'),
                    extracted_brand=extracted_data.get('brand'),
                    extracted_quantity=extracted_data.get('quantity') or extracted_data.get('extracted_quantity'),
                    extracted_amount=extracted_data.get('amount') or extracted_data.get('extracted_amount'),
                    code_no=extracted_data.get('code_no') or extracted_data.get('customer_code'),
                    reference=extracted_data.get('reference'),
                    net_value=_to_decimal_safe(extracted_data.get('net_value') or extracted_data.get('net')),
                    vat_amount=_to_decimal_safe(extracted_data.get('vat_amount') or extracted_data.get('vat')),
                    gross_value=_to_decimal_safe(extracted_data.get('gross_value') or extracted_data.get('gross')),
                    extracted_data_json=extracted_data,
                    confidence_overall=extracted_data.get('confidence_overall', 80),
                )

                # Persist items
                try:
                    _set_extraction_progress(document_scan_id, 'processing', 70, 'Processing items...')
                    
                    items = extracted_data.get('items') or extracted_data.get('structured_data', {}).get('items')
                    if items and isinstance(items, list):
                        from decimal import Decimal
                        for idx, it in enumerate(items, start=1):
                            code = it.get('code') or it.get('item_code') or None
                            desc = it.get('description') or it.get('desc') or it.get('description_full') or str(it.get('description') or '')
                            qty = it.get('qty') or it.get('quantity')
                            unit = it.get('unit') or it.get('type')
                            rate = it.get('rate')
                            value = it.get('value')

                            def _to_decimal(v):
                                try:
                                    if v is None:
                                        return None
                                    if isinstance(v, (int, float, Decimal)):
                                        return Decimal(str(v))
                                    v_clean = str(v).replace(',', '').strip()
                                    return Decimal(v_clean)
                                except Exception:
                                    return None

                            qty_d = _to_decimal(qty)
                            rate_d = _to_decimal(rate)
                            value_d = _to_decimal(value)

                            DocumentExtractionItem.objects.create(
                                extraction=extraction,
                                line_no=idx,
                                code=code,
                                description=desc,
                                qty=qty_d,
                                unit=unit,
                                rate=rate_d,
                                value=value_d,
                            )
                except Exception as e:
                    logger.warning(f"Failed to save extracted items: {e}")

                _set_extraction_progress(document_scan_id, 'processing', 90, 'Finalizing...')

                doc_scan.extraction_status = 'completed'
                from django.utils import timezone
                doc_scan.extracted_at = timezone.now()
                doc_scan.save()

                # Try to build matches: check vehicle and customer existence
                from tracker.utils import get_user_branch
                try:
                    user_branch = get_user_branch(doc_scan.uploaded_by) if doc_scan.uploaded_by else None
                    matches = {}
                    if extracted_data.get('plate_number') and user_branch:
                        from tracker.models import Vehicle
                        v = Vehicle.objects.filter(plate_number__iexact=extracted_data.get('plate_number'), customer__branch=user_branch).select_related('customer').first()
                        if v:
                            matches['vehicle'] = {'id': v.id, 'plate': v.plate_number, 'make': v.make, 'model': v.model}
                            matches['customer'] = {'id': v.customer.id, 'name': v.customer.full_name, 'phone': v.customer.phone}
                    
                    # Try to apply auto-apply logic if order attached
                    if doc_scan.order:
                        _try_auto_apply_extraction(doc_scan, extraction, extracted_data, user_branch)
                except Exception as e:
                    logger.warning(f"Error handling auto-apply: {e}")

                _set_extraction_progress(document_scan_id, 'completed', 100, 'Invoice processed successfully')
            else:
                doc_scan.extraction_status = 'failed'
                doc_scan.extraction_error = extracted_data.get('error')
                doc_scan.save()
                _set_extraction_progress(document_scan_id, 'failed', 0, extracted_data.get('error', 'Extraction failed'))
        except Exception as e:
            doc_scan.extraction_status = 'failed'
            doc_scan.extraction_error = str(e)
            doc_scan.save()
            logger.error(f"Error extracting document: {str(e)}")
            _set_extraction_progress(document_scan_id, 'failed', 0, str(e))

    except DocumentScan.DoesNotExist:
        logger.error(f"DocumentScan {document_scan_id} not found")
        _set_extraction_progress(document_scan_id, 'failed', 0, 'Document not found')
    except Exception as e:
        logger.error(f"Error in extraction worker: {str(e)}")
        _set_extraction_progress(document_scan_id, 'failed', 0, str(e))


def _try_auto_apply_extraction(doc_scan, extraction, extracted_data, user_branch):
    """Try to auto-apply extraction to attached order if confidence is high."""
    try:
        order = doc_scan.order
        if not order:
            return
        
        conf = int(extraction.confidence_overall or 0)
        AUTO_APPLY_THRESHOLD = 85
        
        if conf < AUTO_APPLY_THRESHOLD:
            return
        
        from tracker.models import Customer, Vehicle
        
        # Ensure customer
        customer = order.customer
        if not customer:
            cust_name = extraction.extracted_customer_name or extracted_data.get('customer_name') or f'Customer {order.order_number}'
            cust_phone = extraction.extracted_customer_phone or extracted_data.get('customer_phone') or ''
            customer = Customer.objects.create(branch=user_branch, full_name=cust_name, phone=cust_phone, customer_type='personal')
            order.customer = customer
        else:
            if extraction.extracted_customer_name:
                customer.full_name = extraction.extracted_customer_name
            if extraction.extracted_customer_phone:
                customer.phone = extraction.extracted_customer_phone
            if extraction.extracted_customer_email:
                customer.email = extraction.extracted_customer_email
            customer.save()

        # Vehicle handling
        extracted_plate = (extraction.extracted_vehicle_plate or extracted_data.get('plate_number') or extracted_data.get('vehicle_plate') or '').strip()
        if extracted_plate:
            plate_norm = extracted_plate.upper()
            existing_vehicle = Vehicle.objects.filter(plate_number__iexact=plate_norm, customer__branch=user_branch).select_related('customer').first()
            if existing_vehicle:
                vehicle_obj = existing_vehicle
                if vehicle_obj.customer != customer:
                    vehicle_obj.customer = customer
                    vehicle_obj.save()
                order.vehicle = vehicle_obj
            else:
                vehicle_obj = Vehicle.objects.create(
                    customer=customer,
                    plate_number=plate_norm,
                    make=(extraction.extracted_vehicle_make or extracted_data.get('vehicle_make') or ''),
                    model=(extraction.extracted_vehicle_model or extracted_data.get('vehicle_model') or ''),
                    vehicle_type=(extracted_data.get('vehicle_type') or '')
                )
                order.vehicle = vehicle_obj

        # Order fields
        if extraction.extracted_order_description:
            order.description = extraction.extracted_order_description
        if extraction.extracted_item_name:
            order.item_name = extraction.extracted_item_name
        if extraction.extracted_brand:
            order.brand = extraction.extracted_brand
        if extraction.extracted_quantity:
            try:
                order.quantity = int(extraction.extracted_quantity)
            except Exception:
                pass
        # amount -> gross_value or amount
        if extraction.extracted_amount:
            try:
                from decimal import Decimal
                amt = Decimal(str(extraction.extracted_amount))
                if hasattr(order, 'gross_value'):
                    order.gross_value = amt
                elif hasattr(order, 'amount'):
                    order.amount = amt
            except Exception:
                pass

        order.save()
    except Exception as e:
        logger.warning(f"Auto-apply failed: {e}")


def get_extraction_progress(document_scan_id):
    """
    Get current extraction progress.
    
    Args:
        document_scan_id: ID of DocumentScan
    
    Returns:
        Dict with status, progress, message
    """
    cache_key = f"extraction_progress_{document_scan_id}"
    cached = cache.get(cache_key)
    
    if cached:
        return cached
    
    # Fallback to database status
    try:
        doc_scan = DocumentScan.objects.get(id=document_scan_id)
        return {
            'status': doc_scan.extraction_status,
            'progress': 100 if doc_scan.extraction_status == 'completed' else (0 if doc_scan.extraction_status == 'failed' else 50),
            'message': doc_scan.extraction_error or ''
        }
    except DocumentScan.DoesNotExist:
        return {
            'status': 'failed',
            'progress': 0,
            'message': 'Document not found'
        }


def _set_extraction_progress(document_scan_id, status, progress, message):
    """
    Set extraction progress in cache.
    
    Args:
        document_scan_id: ID of DocumentScan
        status: Status string (processing, completed, failed)
        progress: Progress percentage (0-100)
        message: Status message
    """
    cache_key = f"extraction_progress_{document_scan_id}"
    data = {
        'status': status,
        'progress': progress,
        'message': message
    }
    cache.set(cache_key, data, timeout=3600)  # Cache for 1 hour
