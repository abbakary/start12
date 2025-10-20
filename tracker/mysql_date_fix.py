"""
MySQL Date Compatibility Fixes

The main issue is that MySQL doesn't support __date lookups the same way as SQLite.
We need to use datetime ranges instead of __date filters.
"""

from django.utils import timezone
from datetime import datetime, time, timedelta

def get_date_range(date_obj):
    """Convert a date to a datetime range for MySQL compatibility"""
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    start_datetime = timezone.make_aware(datetime.combine(date_obj, time.min))
    end_datetime = timezone.make_aware(datetime.combine(date_obj, time.max))
    
    return start_datetime, end_datetime

def get_period_range(period):
    """Get datetime range for a period that works with MySQL"""
    today = timezone.now().date()
    
    if period == '1month':
        start_date = today - timedelta(days=30)
    elif period == '3months':
        start_date = today - timedelta(days=90)
    elif period == '1year':
        start_date = today - timedelta(days=365)
    else:  # 6months default
        start_date = today - timedelta(days=180)
    
    # Convert to datetime for MySQL compatibility
    start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
    end_datetime = timezone.make_aware(datetime.combine(today, time.max))
    
    return start_datetime, end_datetime

def get_today_range():
    """Get today's datetime range for MySQL compatibility"""
    today = timezone.now().date()
    return get_date_range(today)

def get_month_start_range():
    """Get current month start datetime range for MySQL compatibility"""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    return timezone.make_aware(datetime.combine(month_start, time.min)), timezone.now()