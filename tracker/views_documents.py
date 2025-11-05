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
from .extraction_utils import process_invoice_extraction
from .utils import get_user_branch

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def upload_document(request):
    """Upload a document, optionally attach to an existing order, and start async extraction.

    Accepts FormData with:
    - file (required)
    - vehicle_plate (optional)
    - customer_phone (optional)
    - document_type (optional, defaults to 'invoice')
    - order_id (optional) — attach the upload to this order

    Returns immediately with document_id and extraction_id.
    Extraction happens in background. Use get_document_status to poll progress.
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
                extraction_status='pending'
            )

        # Start async extraction in background thread
        from .utils.async_extraction import start_extraction_task
        start_extraction_task(doc_scan.id)

        # Return immediately with document info
        return JsonResponse({
            'success': True,
            'document_id': doc_scan.id,
            'extraction_id': None,  # Will be populated after extraction completes
            'status': 'pending',
            'message': 'Invoice uploaded and queued for processing'
        })

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
