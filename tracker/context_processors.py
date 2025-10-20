from django.utils import timezone
from datetime import timedelta
from .models import Order


def header_notifications(request):
    """Provide header notification metrics for stale in-progress orders (>24h).
    Uses values computed by AutoProgressOrdersMiddleware when available to avoid extra queries.
    """
    count = getattr(request, 'stale_in_progress_count', None)
    items = getattr(request, 'stale_in_progress_list', None)
    if count is not None and items is not None:
        return {
            'stale_in_progress_count': count,
            'stale_in_progress_orders': items,
        }

    try:
        from .utils import scope_queryset
        cutoff = timezone.now() - timedelta(hours=24)
        qs = scope_queryset(Order.objects.select_related('customer'), request.user, request).filter(status='in_progress', started_at__lte=cutoff)
        data = list(qs.order_by('-started_at')[:5].values('id','order_number','customer__full_name','started_at'))
        return {
            'stale_in_progress_count': qs.count(),
            'stale_in_progress_orders': data,
        }
    except Exception:
        return {
            'stale_in_progress_count': 0,
            'stale_in_progress_orders': [],
        }
