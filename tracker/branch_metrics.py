from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpRequest
from django.utils import timezone
from .models import Branch, Order, Customer

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def api_branch_metrics(request: HttpRequest):
    period = (request.GET.get('period') or 'monthly').lower()
    today = timezone.localdate()
    if period == 'daily':
        start_date = today
        end_date = today
    elif period == 'weekly':
        start_date = today - timezone.timedelta(days=6)
        end_date = today
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        start_date = today - timezone.timedelta(days=29)
        end_date = today

    if request.user.is_superuser:
        branches = Branch.objects.filter(is_active=True).order_by('name')
    else:
        b = getattr(getattr(request.user, 'profile', None), 'branch', None)
        branches = Branch.objects.filter(id=b.id) if b else Branch.objects.none()

    data = []
    for b in branches:
        oqs = Order.objects.filter(branch=b, created_at__date__gte=start_date, created_at__date__lte=end_date)
        cqs = Customer.objects.filter(branch=b, registration_date__date__gte=start_date, registration_date__date__lte=end_date)
        total = oqs.count()
        completed = oqs.filter(status='completed').count()
        in_progress = oqs.filter(status__in=['created','in_progress']).count()
        cancelled = oqs.filter(status='cancelled').count()
        overdue = oqs.filter(status='overdue').count()
        data.append({
            'branch': {'id': b.id, 'name': b.name, 'code': b.code, 'region': b.region},
            'totals': {
                'orders': total,
                'completed': completed,
                'in_progress': in_progress,
                'cancelled': cancelled,
                'overdue': overdue,
                'new_customers': cqs.count(),
            }
        })
    return JsonResponse({'period': period, 'start': start_date.isoformat(), 'end': end_date.isoformat(), 'branches': data})
