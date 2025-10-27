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
    """Upload and extract data from a document (quotation, invoice, etc.)"""
    try:
        if not request.FILES.get('file'):
            return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        vehicle_plate = request.POST.get('vehicle_plate', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        order_id = request.POST.get('order_id')
        document_type = request.POST.get('document_type', 'quotation')
        
        # Validate file size (max 50MB)
        if uploaded_file.size > 50 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'File size exceeds 50MB limit'}, status=400)
        
        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/bmp', 'image/tiff']
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({'success': False, 'error': 'File type not supported'}, status=400)
        
        user_branch = get_user_branch(request.user)
        
        # Create DocumentScan record
        with transaction.atomic():
            doc_scan = DocumentScan.objects.create(
                order_id=order_id if order_id else None,
                vehicle_plate=vehicle_plate or None,
                customer_phone=customer_phone or None,
                file=uploaded_file,
                document_type=document_type,
                uploaded_by=request.user,
                file_name=uploaded_file.name,
                file_size=uploaded_file.size,
                file_mime_type=uploaded_file.content_type,
                extraction_status='processing'
            )
            
            # Process extraction asynchronously
            try:
                extraction_result = _perform_extraction(doc_scan)
                
                # Create or update DocumentExtraction
                extraction_data = extraction_result.get('extraction_data', {})
                
                doc_extraction = DocumentExtraction.objects.create(
                    document=doc_scan,
                    raw_text=extraction_data.get('raw_text', ''),
                    extracted_customer_name=extraction_data.get('extracted_customer_name'),
                    extracted_customer_phone=extraction_data.get('extracted_customer_phone'),
                    extracted_customer_email=extraction_data.get('extracted_customer_email'),
                    extracted_vehicle_plate=extraction_data.get('extracted_vehicle_plate'),
                    extracted_vehicle_make=extraction_data.get('extracted_vehicle_make'),
                    extracted_vehicle_model=extraction_data.get('extracted_vehicle_model'),
                    extracted_order_description=extraction_data.get('extracted_order_description'),
                    extracted_service_type=extraction_data.get('extracted_service_type'),
                    extracted_item_name=extraction_data.get('extracted_item_name'),
                    extracted_brand=extraction_data.get('extracted_brand'),
                    extracted_quantity=extraction_data.get('extracted_quantity'),
                    extracted_tire_type=extraction_data.get('extracted_tire_type'),
                    extracted_amount=extraction_data.get('extracted_amount'),
                    confidence_overall=extraction_data.get('confidence_overall', 0),
                    extracted_data_json=extraction_data.get('extracted_data_json', {}),
                )
                
                # Update DocumentScan status
                doc_scan.extraction_status = 'completed'
                doc_scan.extracted_at = timezone.now()
                doc_scan.save(update_fields=['extraction_status', 'extracted_at'])
                
                # Match with existing records
                matches = match_document_to_records(
                    extraction_result.get('extraction_data', {}),
                    vehicle_plate=extraction_data.get('extracted_vehicle_plate') or vehicle_plate,
                    customer_phone=extraction_data.get('extracted_customer_phone') or customer_phone
                )
                
                return JsonResponse({
                    'success': True,
                    'document_id': doc_scan.id,
                    'extraction_id': doc_extraction.id,
                    'file_name': doc_scan.file_name,
                    'extracted_data': {
                        'customer_name': doc_extraction.extracted_customer_name,
                        'customer_phone': doc_extraction.extracted_customer_phone,
                        'vehicle_plate': doc_extraction.extracted_vehicle_plate,
                        'vehicle_make': doc_extraction.extracted_vehicle_make,
                        'service_type': doc_extraction.extracted_service_type,
                        'item_name': doc_extraction.extracted_item_name,
                        'quantity': doc_extraction.extracted_quantity,
                        'amount': doc_extraction.extracted_amount,
                        'confidence': doc_extraction.confidence_overall,
                    },
                    'matches': matches,
                    'message': 'Document uploaded and processed successfully'
                })
            
            except Exception as e:
                logger.error(f"Document extraction failed: {str(e)}")
                doc_scan.extraction_status = 'failed'
                doc_scan.extraction_error = str(e)
                doc_scan.save(update_fields=['extraction_status', 'extraction_error'])
                
                return JsonResponse({
                    'success': False,
                    'error': f'Document extraction failed: {str(e)}',
                    'document_id': doc_scan.id
                }, status=400)
    
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _perform_extraction(doc_scan: DocumentScan):
    """Perform actual document extraction"""
    # Get file path
    file_path = doc_scan.file.path
    
    # Extract data
    extractor = DocumentExtractor()
    extraction_result = extractor.extract_from_file(file_path)
    
    if not extraction_result.get('success'):
        raise Exception(extraction_result.get('error', 'Extraction failed'))
    
    # Prepare structured extraction data
    prep_data = extractor.prepare_extraction_data(extraction_result)
    extraction_result['extraction_data'] = prep_data
    
    return extraction_result


@login_required
@require_http_methods(["GET"])
def get_document_extraction(request, doc_id):
    """Retrieve extraction data for a document"""
    try:
        doc_scan = get_object_or_404(DocumentScan, id=doc_id)
        extraction = get_object_or_404(DocumentExtraction, document=doc_scan)
        
        return JsonResponse({
            'success': True,
            'document': {
                'id': doc_scan.id,
                'file_name': doc_scan.file_name,
                'document_type': doc_scan.document_type,
                'uploaded_at': doc_scan.uploaded_at.isoformat(),
                'extraction_status': doc_scan.extraction_status,
            },
            'extraction': {
                'id': extraction.id,
                'customer_name': extraction.extracted_customer_name,
                'customer_phone': extraction.extracted_customer_phone,
                'customer_email': extraction.extracted_customer_email,
                'vehicle_plate': extraction.extracted_vehicle_plate,
                'vehicle_make': extraction.extracted_vehicle_make,
                'vehicle_model': extraction.extracted_vehicle_model,
                'order_description': extraction.extracted_order_description,
                'service_type': extraction.extracted_service_type,
                'item_name': extraction.extracted_item_name,
                'brand': extraction.extracted_brand,
                'quantity': extraction.extracted_quantity,
                'amount': extraction.extracted_amount,
                'confidence': extraction.confidence_overall,
                'raw_text': extraction.raw_text[:1000] if extraction.raw_text else None,
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving extraction: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def create_order_from_document(request):
    """Create or update order from extracted document data"""
    try:
        data = json.loads(request.body)
        extraction_id = data.get('extraction_id')
        use_extracted = data.get('use_extracted', True)
        
        # Get extraction
        extraction = get_object_or_404(DocumentExtraction, id=extraction_id)
        doc_scan = extraction.document
        
        user_branch = get_user_branch(request.user)
        
        with transaction.atomic():
            # Check if customer exists or create
            customer_phone = data.get('customer_phone') or extraction.extracted_customer_phone
            customer_name = data.get('customer_name') or extraction.extracted_customer_name
            
            if not customer_phone or not customer_name:
                return JsonResponse({
                    'success': False,
                    'error': 'Customer name and phone are required'
                }, status=400)
            
            # Look for existing customer
            customer = Customer.objects.filter(
                branch=user_branch,
                phone=customer_phone
            ).first()
            
            if not customer:
                # Create new customer from extracted data
                customer = Customer.objects.create(
                    branch=user_branch,
                    full_name=customer_name,
                    phone=customer_phone,
                    email=data.get('customer_email') or extraction.extracted_customer_email,
                    address=data.get('customer_address'),
                    customer_type=data.get('customer_type', 'personal'),
                )
            
            # Check if vehicle exists or create
            vehicle = None
            vehicle_plate = data.get('vehicle_plate') or extraction.extracted_vehicle_plate
            
            if vehicle_plate:
                vehicle = Vehicle.objects.filter(
                    customer=customer,
                    plate_number=vehicle_plate
                ).first()
                
                if not vehicle:
                    vehicle = Vehicle.objects.create(
                        customer=customer,
                        plate_number=vehicle_plate,
                        make=data.get('vehicle_make') or extraction.extracted_vehicle_make,
                        model=data.get('vehicle_model') or extraction.extracted_vehicle_model,
                        vehicle_type=data.get('vehicle_type') or extraction.extracted_vehicle_type,
                    )
            
            # Create order
            order = Order.objects.create(
                customer=customer,
                vehicle=vehicle,
                branch=user_branch,
                type=data.get('order_type', 'service'),
                status='created',
                description=data.get('description') or extraction.extracted_order_description,
                item_name=data.get('item_name') or extraction.extracted_item_name,
                brand=data.get('brand') or extraction.extracted_brand,
                quantity=int(data.get('quantity') or extraction.extracted_quantity or 0) or None,
                tire_type=data.get('tire_type') or extraction.extracted_tire_type,
                priority=data.get('priority', 'medium'),
            )
            
            # Link document to order
            doc_scan.order = order
            doc_scan.save(update_fields=['order'])
            
            # Update order with job card number if provided
            if data.get('job_card_number'):
                order.job_card_number = data.get('job_card_number')
                order.save(update_fields=['job_card_number'])
            
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'customer_id': customer.id,
                'vehicle_id': vehicle.id if vehicle else None,
                'message': 'Order created successfully from document'
            })
    
    except Exception as e:
        logger.error(f"Error creating order from document: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def verify_and_update_extraction(request):
    """Verify and update extracted data before creating order"""
    try:
        data = json.loads(request.body)
        extraction_id = data.get('extraction_id')
        
        extraction = get_object_or_404(DocumentExtraction, id=extraction_id)
        
        # Update extraction with verified/corrected data
        updates = {}
        
        if 'customer_name' in data:
            updates['extracted_customer_name'] = data['customer_name']
        if 'customer_phone' in data:
            updates['extracted_customer_phone'] = data['customer_phone']
        if 'vehicle_plate' in data:
            updates['extracted_vehicle_plate'] = data['vehicle_plate']
        if 'vehicle_make' in data:
            updates['extracted_vehicle_make'] = data['vehicle_make']
        if 'quantity' in data:
            updates['extracted_quantity'] = data['quantity']
        
        if updates:
            for key, value in updates.items():
                setattr(extraction, key, value)
            extraction.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Extraction data updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error verifying extraction: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def search_by_job_card(request):
    """Search for order by job card number or vehicle plate"""
    try:
        data = json.loads(request.body)
        job_card = data.get('job_card_number', '').strip()
        vehicle_plate = data.get('vehicle_plate', '').strip()
        
        user_branch = get_user_branch(request.user)
        
        results = {
            'order': None,
            'customer': None,
            'vehicle': None,
        }
        
        # Search by job card
        if job_card:
            order = Order.objects.filter(
                job_card_number=job_card,
                branch=user_branch
            ).first()
            
            if order:
                results['order'] = {
                    'id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'type': order.type,
                    'created_at': order.created_at.isoformat(),
                }
                results['customer'] = {
                    'id': order.customer.id,
                    'name': order.customer.full_name,
                    'phone': order.customer.phone,
                }
                if order.vehicle:
                    results['vehicle'] = {
                        'id': order.vehicle.id,
                        'plate': order.vehicle.plate_number,
                        'make': order.vehicle.make,
                        'model': order.vehicle.model,
                    }
        
        # Search by vehicle plate
        elif vehicle_plate:
            vehicle = Vehicle.objects.filter(
                plate_number__iexact=vehicle_plate,
                customer__branch=user_branch
            ).first()
            
            if vehicle:
                results['vehicle'] = {
                    'id': vehicle.id,
                    'plate': vehicle.plate_number,
                    'make': vehicle.make,
                    'model': vehicle.model,
                }
                results['customer'] = {
                    'id': vehicle.customer.id,
                    'name': vehicle.customer.full_name,
                    'phone': vehicle.customer.phone,
                }
                
                # Get most recent order
                recent_order = vehicle.orders.order_by('-created_at').first()
                if recent_order:
                    results['order'] = {
                        'id': recent_order.id,
                        'order_number': recent_order.order_number,
                        'status': recent_order.status,
                        'type': recent_order.type,
                        'created_at': recent_order.created_at.isoformat(),
                    }
        
        return JsonResponse({
            'success': True,
            'found': any(results.values()),
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Error searching by job card: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
