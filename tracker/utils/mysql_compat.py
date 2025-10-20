"""
MySQL Compatibility Utilities
Fixes date filtering issues when switching from SQLite to MySQL
"""

from django.utils import timezone
from datetime import datetime, time, timedelta
from django.db.models import Q

def get_date_range(date_obj):
    """Convert a date to datetime range for MySQL compatibility"""
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    start_dt = timezone.make_aware(datetime.combine(date_obj, time.min))
    end_dt = timezone.make_aware(datetime.combine(date_obj, time.max))
    return start_dt, end_dt

def today_filter():
    """Get today's date filter for MySQL compatibility"""
    today = timezone.now().date()
    start_dt, end_dt = get_date_range(today)
    return Q(created_at__gte=start_dt, created_at__lte=end_dt)

def date_filter(date_field, target_date):
    """Get date filter for any date field"""
    start_dt, end_dt = get_date_range(target_date)
    return Q(**{f'{date_field}__gte': start_dt, f'{date_field}__lte': end_dt})

def month_start_filter(date_field='created_at'):
    """Get filter for current month start"""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    start_dt = timezone.make_aware(datetime.combine(month_start, time.min))
    return Q(**{f'{date_field}__gte': start_dt})

def period_filter(days, date_field='created_at'):
    """Get filter for last N days"""
    today = timezone.now().date()
    start_date = today - timedelta(days=days)
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    return Q(**{f'{date_field}__gte': start_dt})