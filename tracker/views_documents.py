import json
import os
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import DocumentScan, DocumentExtraction, Order, Vehicle, Customer, Branch
from .utils.document_extraction import DocumentExtractor, extract_document, match_document_to_records
from .utils import get_user_branch

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def upload_document(request):
    """Upload a document, optionally attach to an existing order, and run extraction.

    Accepts FormData with:
    - file (required)
    - vehicle_plate (optional)
    - customer_phone (optional)
    - document_type (optional)
    - order_id (optional) — attach the upload to this order
    """
    try:
        file = request.FILES.get('file')
        vehicle_plate = request.POST.get('vehicle_plate', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        document_type = request.POST.get('document_type', 'invoice')
        order_id = request.POST.get('order_id')

        if not file:
            return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)

        user_branch = get_user_branch(request.user)
        order = None
        if order_id:
            try:
                order = Order.objects.get(id=int(order_id), branch=user_branch)
            except Exception:
                order = None

        with transaction.atomic():
            doc_scan = DocumentScan.objects.create(
                order=order,
                vehicle_plate=vehicle_plate or (order.vehicle.plate_number if order and order.vehicle else ''),
                customer_phone=customer_phone or (order.customer.phone if order and order.customer else ''),
                file=file,
                document_type=document_type,
                uploaded_by=request.user,
                file_name=file.name,
                file_size=file.size,
                file_mime_type=file.content_type,
                extraction_status='processing'
            )

            # Run extraction using existing utility
            try:
                extracted_data = process_invoice_extraction(doc_scan)

                if 'error' not in extracted_data:
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

                    doc_scan.extraction_status = 'completed'
                    doc_scan.extracted_at = timezone.now()
                    doc_scan.save()

                    # Try to build matches: check vehicle and customer existence
                    matches = {}
                    if extracted_data.get('plate_number'):
                        v = Vehicle.objects.filter(plate_number__iexact=extracted_data.get('plate_number'), customer__branch=user_branch).select_related('customer').first()
                        if v:
                            matches['vehicle'] = {'id': v.id, 'plate': v.plate_number, 'make': v.make, 'model': v.model}
                            matches['customer'] = {'id': v.customer.id, 'name': v.customer.full_name, 'phone': v.customer.phone}

                    return JsonResponse({'success': True, 'document_id': doc_scan.id, 'extraction_id': extraction.id, 'extracted_data': extracted_data, 'matches': matches})
                else:
                    doc_scan.extraction_status = 'failed'
                    doc_scan.extraction_error = extracted_data.get('error')
                    doc_scan.save()
                    return JsonResponse({'success': False, 'error': extracted_data.get('error')}, status=400)
            except Exception as e:
                doc_scan.extraction_status = 'failed'
                doc_scan.extraction_error = str(e)
                doc_scan.save()
                logger.error(f"Error extracting document: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _perform_extraction(doc_scan: DocumentScan):
    """Document extraction has been removed."""
    raise NotImplementedError('Document extraction removed')


@login_required
@require_http_methods(["GET"])
def get_document_extraction(request, doc_id):
    return JsonResponse({'success': False, 'error': 'Document extraction retrieval disabled'}, status=410)


@login_required
@require_http_methods(["POST"])
def create_order_from_document(request):
    return JsonResponse({'success': False, 'error': 'Create order from document disabled'}, status=410)


@login_required
@require_http_methods(["POST"])
def verify_and_update_extraction(request):
    return JsonResponse({'success': False, 'error': 'Verification of extraction disabled'}, status=410)


@login_required
@require_http_methods(["POST"])
def search_by_job_card(request):
    return JsonResponse({'success': False, 'error': 'Search by job card disabled'}, status=410)
@login_required
@require_http_methods(["POST"])
def start_quick_order(request):
    """Start a quick order with job card number, to be filled later with document"""
    try:
        data = json.loads(request.body)
        job_card_number = data.get('job_card_number', '').strip()
        vehicle_plate = data.get('vehicle_plate', '').strip()
        
        if not job_card_number:
            return JsonResponse({
                'success': False,
                'error': 'Job card number is required'
            }, status=400)
        
        user_branch = get_user_branch(request.user)
        
        # Check if order already exists
        existing_order = Order.objects.filter(
            job_card_number=job_card_number,
            branch=user_branch
        ).first()
        
        if existing_order:
            return JsonResponse({
                'success': False,
                'error': 'Order with this job card already exists',
                'order_id': existing_order.id,
                'order_number': existing_order.order_number,
            }, status=400)
        
        # Create temporary order
        temp_customer_name = f"Customer {job_card_number}"
        
        # Find existing customer by vehicle plate if provided
        customer = None
        vehicle = None
        
        if vehicle_plate:
            vehicle = Vehicle.objects.filter(
                plate_number__iexact=vehicle_plate,
                customer__branch=user_branch
            ).first()
            
            if vehicle:
                customer = vehicle.customer
        
        # Create customer if not found
        if not customer:
            customer = Customer.objects.create(
                branch=user_branch,
                full_name=temp_customer_name,
                phone='pending',  # To be updated
                customer_type='personal',
            )
        
        # Create order
        order = Order.objects.create(
            customer=customer,
            vehicle=vehicle,
            branch=user_branch,
            type='service',
            status='created',
            job_card_number=job_card_number,
            description=f"Order started with job card {job_card_number}",
        )
        
        # Set start time
        order.started_at = timezone.now()
        order.save(update_fields=['started_at'])
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'job_card_number': order.job_card_number,
            'message': 'Quick order started. Upload document to fill in details.'
        })
    
    except Exception as e:
        logger.error(f"Error starting quick order: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
