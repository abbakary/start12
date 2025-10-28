"""
Views for quick order start workflow and started orders management.
Allows users to quickly start an order with plate number, then proceed with document extraction.
"""

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction

from .models import Order, Customer, Vehicle, Branch, DocumentScan, DocumentExtraction
from .utils import get_user_branch
from .extraction_utils import process_invoice_extraction

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_start_order(request):
    """
    API endpoint to start a new order with just a vehicle plate number.
    Creates a minimal order record with started_at timestamp.
    
    POST body:
    {
        "plate_number": "ABC 123 XYZ",
        "order_type": "service|sales|inquiry" (optional, defaults to "service")
    }
    
    Response:
    {
        "success": true,
        "order_id": 123,
        "order_number": "ORD20240101120000XXXX",
        "plate_number": "ABC 123 XYZ",
        "started_at": "2024-01-01T12:00:00Z"
    }
    """
    try:
        data = json.loads(request.body)
        plate_number = (data.get('plate_number') or '').strip().upper()
        order_type = data.get('order_type', 'service')
        
        if not plate_number:
            return JsonResponse({
                'success': False,
                'error': 'Vehicle plate number is required'
            }, status=400)
        
        if order_type not in ['service', 'sales', 'inquiry']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid order type'
            }, status=400)
        
        user_branch = get_user_branch(request.user)
        
        with transaction.atomic():
            # Create a minimal customer for the order (will be updated later)
            # Use plate number as temporary identifier
            customer, _ = Customer.objects.get_or_create(
                branch=user_branch,
                phone=f"TEMP_{plate_number}",
                defaults={
                    'full_name': f'Pending - {plate_number}',
                    'customer_type': 'personal',
                }
            )
            
            # Try to find existing vehicle by plate
            vehicle, vehicle_created = Vehicle.objects.get_or_create(
                customer=customer,
                plate_number=plate_number,
                defaults={
                    'vehicle_type': '',
                    'make': '',
                    'model': '',
                }
            )
            
            # Create the order
            order = Order.objects.create(
                customer=customer,
                vehicle=vehicle,
                branch=user_branch,
                type=order_type,
                status='created',
                started_at=timezone.now(),
                description=f"Order started for {plate_number}",
                priority='medium',
            )
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'plate_number': plate_number,
            'started_at': order.started_at.isoformat(),
            'message': 'Order started successfully. You can now continue with customer registration or document upload.'
        }, status=201)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error starting order: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def started_orders_dashboard(request):
    """
    Display all started orders (status='created') for the current branch.
    Shows orders that have been initiated but not yet completed.
    Grouped by plate number for easy continuation.
    
    GET params:
    - status: Filter by order status (default: 'created')
    - sort_by: Sort orders by 'started_at', 'plate_number', 'order_type' (default: '-started_at')
    - search: Search by plate number or customer name
    """
    user_branch = get_user_branch(request.user)
    status_filter = request.GET.get('status', 'created')
    sort_by = request.GET.get('sort_by', '-started_at')
    search_query = request.GET.get('search', '').strip()
    
    # Get all started orders for this branch
    orders = Order.objects.filter(
        branch=user_branch,
        status=status_filter
    ).select_related('customer', 'vehicle')
    
    # Apply search filter
    if search_query:
        orders = orders.filter(
            vehicle__plate_number__icontains=search_query
        ) | orders.filter(
            customer__full_name__icontains=search_query
        )
    
    # Apply sorting
    if sort_by in ['-started_at', 'started_at', 'plate_number', 'type']:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-started_at')
    
    # Group orders by plate number
    orders_by_plate = {}
    for order in orders:
        plate = order.vehicle.plate_number if order.vehicle else 'Unknown'
        if plate not in orders_by_plate:
            orders_by_plate[plate] = []
        orders_by_plate[plate].append(order)
    
    # Calculate statistics
    total_started = Order.objects.filter(
        branch=user_branch,
        status='created'
    ).count()
    
    today_started = Order.objects.filter(
        branch=user_branch,
        status='created',
        started_at__date=timezone.now().date()
    ).count()
    
    context = {
        'orders': orders,
        'orders_by_plate': orders_by_plate,
        'total_started': total_started,
        'today_started': today_started,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'title': 'Started Orders',
    }
    
    return render(request, 'tracker/started_orders_dashboard.html', context)


@login_required
def started_order_detail(request, order_id):
    """
    Show detail view for a started order with options to:
    - Upload/scan document for extraction
    - Manually enter customer details
    - Upload document and auto-populate
    - Edit and complete the order
    
    GET params:
    - tab: Active tab ('overview', 'customer', 'vehicle', 'document', 'order_details')
    """
    user_branch = get_user_branch(request.user)
    order = get_object_or_404(Order, id=order_id, branch=user_branch)
    
    if request.method == 'POST':
        # Handle form submissions for different sections
        action = request.POST.get('action')
        
        if action == 'update_customer':
            # Update customer details
            order.customer.full_name = request.POST.get('full_name', order.customer.full_name)
            order.customer.phone = request.POST.get('phone', order.customer.phone)
            order.customer.email = request.POST.get('email', order.customer.email) or None
            order.customer.address = request.POST.get('address', order.customer.address) or None
            order.customer.customer_type = request.POST.get('customer_type', order.customer.customer_type)
            order.customer.save()
            
        elif action == 'update_vehicle':
            # Update vehicle details
            if order.vehicle:
                order.vehicle.make = request.POST.get('make', order.vehicle.make)
                order.vehicle.model = request.POST.get('model', order.vehicle.model)
                order.vehicle.vehicle_type = request.POST.get('vehicle_type', order.vehicle.vehicle_type)
                order.vehicle.save()
        
        elif action == 'upload_document':
            # Handle document upload and extraction
            if 'document' in request.FILES:
                doc_file = request.FILES['document']
                doc_type = request.POST.get('document_type', 'invoice')
                
                with transaction.atomic():
                    doc_scan = DocumentScan.objects.create(
                        order=order,
                        vehicle_plate=order.vehicle.plate_number if order.vehicle else '',
                        customer_phone=order.customer.phone,
                        file=doc_file,
                        document_type=doc_type,
                        uploaded_by=request.user,
                        file_name=doc_file.name,
                        file_size=doc_file.size,
                        file_mime_type=doc_file.content_type,
                        extraction_status='processing'
                    )
                    
                    # Process extraction
                    try:
                        extracted_data = process_invoice_extraction(doc_scan)
                        
                        if 'error' not in extracted_data:
                            extraction = DocumentExtraction.objects.create(
                                document=doc_scan,
                                extracted_customer_name=extracted_data.get('customer_name'),
                                extracted_customer_phone=extracted_data.get('customer_phone'),
                                extracted_customer_email=extracted_data.get('customer_email'),
                                extracted_vehicle_plate=extracted_data.get('plate_number'),
                                extracted_order_description=extracted_data.get('service_description'),
                                extracted_item_name=extracted_data.get('item_name'),
                                extracted_brand=extracted_data.get('brand'),
                                extracted_quantity=extracted_data.get('quantity'),
                                extracted_amount=extracted_data.get('amount'),
                                extracted_data_json=extracted_data,
                                confidence_overall=80,
                            )
                            
                            doc_scan.extraction_status = 'completed'
                            doc_scan.extracted_at = timezone.now()
                        else:
                            doc_scan.extraction_status = 'failed'
                            doc_scan.extraction_error = extracted_data.get('error')
                        
                        doc_scan.save()
                    except Exception as e:
                        doc_scan.extraction_status = 'failed'
                        doc_scan.extraction_error = str(e)
                        doc_scan.save()
                        logger.error(f"Error extracting document: {str(e)}")
        
        elif action == 'complete_order':
            # Mark order as completed
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()
            
            return redirect('tracker:started_orders_dashboard')
    
    # Get related documents and extractions
    documents = DocumentScan.objects.filter(order=order).order_by('-uploaded_at')
    extractions = DocumentExtraction.objects.filter(
        document__order=order
    ).order_by('-extracted_at')
    
    # Get latest extraction for preview
    latest_extraction = extractions.first()
    
    active_tab = request.GET.get('tab', 'overview')
    
    context = {
        'order': order,
        'customer': order.customer,
        'vehicle': order.vehicle,
        'documents': documents,
        'extractions': extractions,
        'latest_extraction': latest_extraction,
        'active_tab': active_tab,
        'title': f'Order {order.order_number}',
    }
    
    return render(request, 'tracker/started_order_detail.html', context)


@login_required
@require_http_methods(["POST"])
def api_apply_extraction_to_order(request):
    """
    API endpoint to apply extracted data to an order.
    
    POST body:
    {
        "order_id": 123,
        "extraction_id": 456,
        "apply_fields": ["customer_name", "customer_phone", "service_description"]
    }
    """
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        extraction_id = data.get('extraction_id')
        apply_fields = data.get('apply_fields', [])
        
        user_branch = get_user_branch(request.user)
        order = get_object_or_404(Order, id=order_id, branch=user_branch)
        extraction = get_object_or_404(DocumentExtraction, id=extraction_id)
        
        with transaction.atomic():
            # Apply customer data
            if 'customer_name' in apply_fields and extraction.extracted_customer_name:
                order.customer.full_name = extraction.extracted_customer_name
            if 'customer_phone' in apply_fields and extraction.extracted_customer_phone:
                order.customer.phone = extraction.extracted_customer_phone
            if 'customer_email' in apply_fields and extraction.extracted_customer_email:
                order.customer.email = extraction.extracted_customer_email
            
            order.customer.save()
            
            # Apply vehicle data
            if order.vehicle:
                if 'vehicle_plate' in apply_fields and extraction.extracted_vehicle_plate:
                    order.vehicle.plate_number = extraction.extracted_vehicle_plate
                if 'vehicle_make' in apply_fields and extraction.extracted_vehicle_make:
                    order.vehicle.make = extraction.extracted_vehicle_make
                if 'vehicle_model' in apply_fields and extraction.extracted_vehicle_model:
                    order.vehicle.model = extraction.extracted_vehicle_model
                
                order.vehicle.save()
            
            # Apply order data
            if 'service_description' in apply_fields and extraction.extracted_order_description:
                order.description = extraction.extracted_order_description
            if 'item_name' in apply_fields and extraction.extracted_item_name:
                order.item_name = extraction.extracted_item_name
            if 'brand' in apply_fields and extraction.extracted_brand:
                order.brand = extraction.extracted_brand
            if 'quantity' in apply_fields and extraction.extracted_quantity:
                try:
                    order.quantity = int(extraction.extracted_quantity)
                except (ValueError, TypeError):
                    pass
            if 'amount' in apply_fields and extraction.extracted_amount:
                pass  # Amount handling (if needed in order model)
            
            order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Extraction data applied to order successfully',
            'order_id': order.id
        })
    
    except Exception as e:
        logger.error(f"Error applying extraction: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_auto_fill_from_extraction(request):
    """
    API endpoint to auto-fill order fields based on latest extraction.
    Returns the extracted data for the client to preview before applying.
    
    POST body:
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
        }
    }
    """
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        user_branch = get_user_branch(request.user)
        order = get_object_or_404(Order, id=order_id, branch=user_branch)
        
        # Get latest extraction for this order
        extraction = DocumentExtraction.objects.filter(
            document__order=order
        ).order_by('-extracted_at').first()
        
        if not extraction:
            return JsonResponse({
                'success': False,
                'error': 'No extraction data found for this order'
            }, status=404)
        
        # Build response with extracted data
        response_data = {
            'customer_name': extraction.extracted_customer_name,
            'customer_phone': extraction.extracted_customer_phone,
            'customer_email': extraction.extracted_customer_email,
            'vehicle_plate': extraction.extracted_vehicle_plate,
            'vehicle_make': extraction.extracted_vehicle_make,
            'vehicle_model': extraction.extracted_vehicle_model,
            'service_description': extraction.extracted_order_description,
            'item_name': extraction.extracted_item_name,
            'brand': extraction.extracted_brand,
            'quantity': extraction.extracted_quantity,
            'amount': extraction.extracted_amount,
            'matched_service': extraction.extracted_data_json.get('matched_service'),
            'estimated_minutes': extraction.extracted_data_json.get('estimated_minutes'),
        }
        
        # Remove None/empty values
        response_data = {k: v for k, v in response_data.items() if v}
        
        return JsonResponse({
            'success': True,
            'data': response_data,
            'extraction_id': extraction.id,
            'confidence': extraction.confidence_overall,
        })
    
    except Exception as e:
        logger.error(f"Error auto-filling from extraction: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
