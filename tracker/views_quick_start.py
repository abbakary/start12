import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction

from .models import Order, Customer, Vehicle, Branch
from .forms import CustomerStep1Form as CustomerForm
from .utils import get_user_branch

logger = logging.getLogger(__name__)


@login_required
def customer_register_with_extraction(request, vehicle_plate=None):
    """
    Customer registration with pre-filled data from document extraction or quick start
    
    GET: Show form (optionally with pre-filled data)
    POST: Save customer and optionally create order
    
    Query params:
    - vehicle_plate: Vehicle plate for quick start flow
    - from_quick_start: Flag to indicate coming from quick start
    """
    vehicle_plate = vehicle_plate or request.GET.get('vehicle_plate', '').strip()
    from_quick_start = request.GET.get('from_quick_start', False)
    
    user_branch = get_user_branch(request.user)
    
    # Try to get pre-filled data from session
    extracted_data = {}
    extracted_document_id = None
    
    if request.method == 'GET':
        # Check if there's extracted data in session (from document upload)
        session_data = request.session.get('extracted_order_data', {})
        if session_data:
            extracted_data = session_data
            extracted_document_id = request.session.get('extracted_document_id')
    
    # Get form
    form = CustomerForm(request.POST or None)
    
    # Pre-fill form with extracted data if available
    if request.method == 'GET' and extracted_data:
        initial_data = {
            'full_name': extracted_data.get('customer_name', ''),
            'phone': extracted_data.get('customer_phone', ''),
            'email': extracted_data.get('customer_email', ''),
            'address': extracted_data.get('customer_address', ''),
            'customer_type': extracted_data.get('customer_type', 'personal'),
        }
        form = CustomerForm(initial=initial_data)
    
    if request.method == 'POST':
        if form.is_valid():
            with transaction.atomic():
                # Save customer
                customer = form.save(commit=False)
                customer.branch = user_branch
                customer.save()
                
                # Create vehicle if plate provided
                vehicle = None
                if vehicle_plate:
                    vehicle, created = Vehicle.objects.get_or_create(
                        customer=customer,
                        plate_number=vehicle_plate,
                        defaults={
                            'make': extracted_data.get('vehicle_make', ''),
                            'model': extracted_data.get('vehicle_model', ''),
                            'vehicle_type': extracted_data.get('vehicle_type', ''),
                        }
                    )
                
                # If this is a quick start flow, create placeholder order
                if from_quick_start:
                    order_start_time = request.session.get('quick_start_time')
                    if order_start_time:
                        order_start_time = timezone.datetime.fromisoformat(order_start_time)
                    else:
                        order_start_time = timezone.now()
                    
                    order = Order.objects.create(
                        customer=customer,
                        vehicle=vehicle,
                        branch=user_branch,
                        type='service',
                        status='created',
                        started_at=order_start_time,
                        description=f"Order started for vehicle {vehicle_plate}",
                    )
                    
                    # Redirect to order edit with extracted data
                    request.session['order_id_with_extraction'] = order.id
                    return redirect('tracker:order_edit', order_id=order.id)
                else:
                    # Regular customer registration, redirect to customers list
                    return redirect('tracker:customers_list')
    
    context = {
        'form': form,
        'vehicle_plate': vehicle_plate,
        'from_quick_start': from_quick_start,
        'extracted_data': extracted_data,
        'title': 'Register Customer',
    }
    
    return render(request, 'tracker/customer_register.html', context)


@login_required
@require_http_methods(["GET"])
def order_create_with_extraction(request, customer_id=None):
    """
    Order creation view with pre-filled data from document extraction
    
    GET params:
    - customer_id: Pre-select customer
    - vehicle_plate: Pre-select vehicle
    """
    customer_id = customer_id or request.GET.get('customer_id')
    vehicle_plate = request.GET.get('vehicle_plate', '').strip()
    
    user_branch = get_user_branch(request.user)
    
    # Get pre-filled data from session
    extracted_data = request.session.get('extracted_order_data', {})
    extracted_document_id = request.session.get('extracted_document_id')
    order_start_time = request.session.get('quick_start_time')
    
    customer = None
    vehicle = None
    
    if customer_id:
        customer = get_object_or_404(Customer, id=customer_id, branch=user_branch)
        
        # Try to find vehicle by plate
        if vehicle_plate:
            vehicle = Vehicle.objects.filter(
                customer=customer,
                plate_number__iexact=vehicle_plate
            ).first()
    
    context = {
        'customer': customer,
        'vehicle': vehicle,
        'vehicle_plate': vehicle_plate,
        'extracted_data': extracted_data,
        'extracted_document_id': extracted_document_id,
        'order_start_time': order_start_time,
        'title': 'Create Order',
    }
    
    return render(request, 'tracker/order_create.html', context)


@login_required
@require_http_methods(["POST"])
def auto_fill_order_from_extraction(request):
    """
    API endpoint to auto-fill order form from extracted document data
    
    POST body:
    {
        "extraction_id": int,
        "order_id": int
    }
    """
    try:
        data = json.loads(request.body)
        extraction_id = data.get('extraction_id')
        order_id = data.get('order_id')
        
        if not extraction_id:
            return JsonResponse({'success': False, 'error': 'extraction_id required'}, status=400)
        
        from .models import DocumentExtraction, Order
        
        extraction = get_object_or_404(DocumentExtraction, id=extraction_id)
        
        # Prepare order update data
        order_data = {
            'description': extraction.extracted_order_description or '',
            'item_name': extraction.extracted_item_name or '',
            'brand': extraction.extracted_brand or '',
            'tire_type': extraction.extracted_tire_type or '',
        }
        
        if extraction.extracted_quantity:
            try:
                order_data['quantity'] = int(extraction.extracted_quantity)
            except (ValueError, TypeError):
                pass
        
        # If order_id provided, update it
        if order_id:
            order = get_object_or_404(Order, id=order_id)
            
            for key, value in order_data.items():
                if value:
                    setattr(order, key, value)
            
            order.save()
        
        return JsonResponse({
            'success': True,
            'data': order_data,
            'message': 'Order auto-filled with extracted data'
        })
    
    except Exception as e:
        logger.error(f"Error auto-filling order: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def detect_and_merge_customer_data(request):
    """
    API endpoint to detect mismatches between extracted and existing customer data
    
    POST body:
    {
        "customer_id": int,
        "extracted_data": { customer fields }
    }
    """
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        extracted_data = data.get('extracted_data', {})
        
        if not customer_id:
            return JsonResponse({'success': False, 'error': 'customer_id required'}, status=400)
        
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Detect mismatches
        mismatches = {}
        
        field_mapping = {
            'full_name': 'customer_name',
            'phone': 'customer_phone',
            'email': 'customer_email',
            'address': 'customer_address',
        }
        
        for db_field, extracted_field in field_mapping.items():
            db_value = getattr(customer, db_field, '') or ''
            extracted_value = extracted_data.get(extracted_field, '') or ''
            
            if db_value and extracted_value and str(db_value).lower() != str(extracted_value).lower():
                mismatches[db_field] = {
                    'existing': db_value,
                    'extracted': extracted_value
                }
        
        if mismatches:
            return JsonResponse({
                'success': True,
                'has_mismatches': True,
                'mismatches': mismatches
            })
        else:
            return JsonResponse({
                'success': True,
                'has_mismatches': False,
                'message': 'No data mismatches found'
            })
    
    except Exception as e:
        logger.error(f"Error detecting mismatches: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def apply_customer_data_merge(request):
    """
    API endpoint to apply customer data merging strategy
    
    POST body:
    {
        "customer_id": int,
        "strategy": "keep_existing" | "override" | "merge",
        "merged_data": { field: value } (for merge strategy)
    }
    """
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        strategy = data.get('strategy', 'keep_existing')
        merged_data = data.get('merged_data', {})
        
        if not customer_id:
            return JsonResponse({'success': False, 'error': 'customer_id required'}, status=400)
        
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Apply merge based on strategy
        if strategy == 'merge' and merged_data:
            for field, value in merged_data.items():
                if hasattr(customer, field):
                    setattr(customer, field, value)
            
            customer.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Customer data updated with merge strategy',
            'customer_id': customer.id
        })
    
    except Exception as e:
        logger.error(f"Error applying merge: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
