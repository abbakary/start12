from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q, F, Max, Min
from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import Customer, Order
from .db_compat import is_mysql, date_filter, period_filter
from .utils import scope_queryset

@login_required
def api_customer_groups_data_fixed(request):
    """Fixed API endpoint with clear time filtering and additional filters"""
    
    # Get parameters
    group = request.GET.get('group', 'all')
    period = request.GET.get('period', '6months')
    activity_filter = request.GET.get('activity', 'all')  # all, active, inactive
    order_type_filter = request.GET.get('order_type', 'all')  # all, service, sales, consultation
    
    # Calculate date range - MySQL compatible
    today = timezone.now().date()
    
    if period == '1month':
        start_date = today - timedelta(days=30)
        period_label = "Last 30 Days"
    elif period == '3months':
        start_date = today - timedelta(days=90)
        period_label = "Last 3 Months"
    elif period == '1year':
        start_date = today - timedelta(days=365)
        period_label = "Last Year"
    else:  # 6months default
        start_date = today - timedelta(days=180)
        period_label = "Last 6 Months"
    
    # Use database-compatible date filtering
    if is_mysql():
        start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
        end_datetime = timezone.make_aware(datetime.combine(today, time.max))
    else:
        # For SQLite, we can use the date directly
        start_datetime = start_date
        end_datetime = today
    
    # Get customer types
    customer_types = dict(Customer.TYPE_CHOICES)
    
    # Build statistics for each customer type
    groups_data = {}
    total_customers = 0
    total_orders = 0
    total_revenue = 0
    
    for customer_type, display_name in customer_types.items():
        # Base customer queryset for this type (scoped by branch)
        customers_qs = scope_queryset(Customer.objects.filter(customer_type=customer_type), request.user, request)

        # Active customer ids determined from branch-scoped orders within period
        orders_base = scope_queryset(Order.objects.all(), request.user, request)
        if is_mysql():
            active_customer_ids = orders_base.filter(
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            ).values_list('customer_id', flat=True).distinct()
        else:
            active_customer_ids = orders_base.filter(
                created_at__date__gte=start_datetime
            ).values_list('customer_id', flat=True).distinct()

        # Apply activity filter
        if activity_filter == 'active':
            customers_qs = customers_qs.filter(id__in=active_customer_ids)
        elif activity_filter == 'inactive':
            customers_qs = customers_qs.exclude(id__in=active_customer_ids)

        # Count customers in this type
        customer_count = customers_qs.count()

        # Orders for this customer type within period (scoped)
        if is_mysql():
            orders_qs = orders_base.filter(
                customer__customer_type=customer_type,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            )
        else:
            orders_qs = orders_base.filter(
                customer__customer_type=customer_type,
                created_at__date__gte=start_datetime
            )

        # Apply order type filter
        if order_type_filter != 'all':
            orders_qs = orders_qs.filter(type=order_type_filter)

        # Calculate metrics
        total_orders_count = orders_qs.count()
        service_orders_count = orders_qs.filter(type='service').count()
        sales_orders_count = orders_qs.filter(type='sales').count()
        consultation_orders_count = orders_qs.filter(type='consultation').count()
        completed_orders_count = orders_qs.filter(status='completed').count()

        # Revenue: sum total_spent for customers with activity in period (scoped)
        if activity_filter in ('active', 'all'):
            revenue = customers_qs.filter(id__in=active_customer_ids).aggregate(total=Sum('total_spent'))['total'] or 0
        else:
            revenue = 0

        # Calculate averages
        avg_orders = round(total_orders_count / customer_count, 1) if customer_count > 0 else 0
        avg_revenue = round(float(revenue) / customer_count, 2) if customer_count > 0 else 0

        groups_data[customer_type] = {
            'name': display_name,
            'customer_count': customer_count,
            'total_orders': total_orders_count,
            'service_orders': service_orders_count,
            'sales_orders': sales_orders_count,
            'consultation_orders': consultation_orders_count,
            'completed_orders': completed_orders_count,
            'total_revenue': float(revenue),
            'avg_orders': avg_orders,
            'avg_revenue': avg_revenue
        }

        total_customers += customer_count
        total_orders += total_orders_count
        total_revenue += float(revenue)
    
    # If specific group requested, get detailed data
    group_details = None
    if group != 'all' and group in customer_types:
        customers = scope_queryset(Customer.objects.filter(customer_type=group), request.user, request).annotate(
            recent_orders=Count('orders', filter=Q(
                orders__created_at__gte=start_datetime,
                orders__created_at__lte=end_datetime
            )),
            service_orders=Count('orders', filter=Q(
                orders__type='service',
                orders__created_at__gte=start_datetime,
                orders__created_at__lte=end_datetime
            )),
            sales_orders=Count('orders', filter=Q(
                orders__type='sales',
                orders__created_at__gte=start_datetime,
                orders__created_at__lte=end_datetime
            )),
            consultation_orders=Count('orders', filter=Q(
                orders__type='consultation',
                orders__created_at__gte=start_datetime,
                orders__created_at__lte=end_datetime
            )),
            completed_orders=Count('orders', filter=Q(
                orders__status='completed',
                orders__created_at__gte=start_datetime,
                orders__created_at__lte=end_datetime
            )),
            last_order_date=Max('orders__created_at'),
            vehicles_count=Count('vehicles', distinct=True)
        ).order_by('-total_spent')
        
        # Convert to list for JSON serialization
        customers_data = []
        for c in customers[:50]:  # Limit to 50 customers
            customers_data.append({
                'id': c.id,
                'full_name': c.full_name,
                'phone': c.phone,
                'email': c.email or '',
                'total_spent': float(c.total_spent or 0),
                'total_orders': c.recent_orders,
                'service_orders': c.service_orders,
                'sales_orders': c.sales_orders,
                'consultation_orders': c.consultation_orders,
                'completed_orders': c.completed_orders,
                'last_order_date': c.last_order_date.isoformat() if c.last_order_date else None,
                'vehicles_count': c.vehicles_count,
                'registration_date': c.registration_date.isoformat() if c.registration_date else None
            })
        
        group_details = {
            'customers': customers_data,
            'stats': groups_data.get(group, {})
        }
    
    return JsonResponse({
        'success': True,
        'groups': groups_data,
        'totals': {
            'customers': total_customers,
            'orders': total_orders,
            'revenue': round(total_revenue, 2)
        },
        'group_details': group_details,
        'period': period,
        'period_label': period_label,
        'filters': {
            'activity': activity_filter,
            'order_type': order_type_filter
        },
        'date_range': {
            'start': start_date.isoformat(),
            'end': today.isoformat()
        }
    })
