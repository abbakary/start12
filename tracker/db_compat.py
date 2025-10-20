"""
Database Compatibility Layer
Handles differences between SQLite and MySQL for date operations
"""

from django.db import connection
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time, timedelta

def is_mysql():
    """Check if we're using MySQL"""
    return 'mysql' in connection.settings_dict['ENGINE']

def date_filter(field_name, target_date):
    """Create date filter that works with both SQLite and MySQL"""
    if is_mysql():
        # MySQL: use datetime range
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        
        start_dt = timezone.make_aware(datetime.combine(target_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(target_date, time.max))
        
        return Q(**{f'{field_name}__gte': start_dt, f'{field_name}__lte': end_dt})
    else:
        # SQLite: use __date lookup
        return Q(**{f'{field_name}__date': target_date})

def today_filter(field_name='created_at'):
    """Get today's date filter"""
    today = timezone.now().date()
    return date_filter(field_name, today)

def period_filter(field_name, days):
    """Get filter for last N days"""
    if is_mysql():
        # MySQL: use datetime range
        start_date = timezone.now().date() - timedelta(days=days)
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
        return Q(**{f'{field_name}__gte': start_dt})
    else:
        # SQLite: use __date lookup
        start_date = timezone.now().date() - timedelta(days=days)
        return Q(**{f'{field_name}__date__gte': start_date})

def month_start_filter(field_name='created_at'):
    """Get filter for current month start"""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    if is_mysql():
        start_dt = timezone.make_aware(datetime.combine(month_start, time.min))
        return Q(**{f'{field_name}__gte': start_dt})
    else:
        return Q(**{f'{field_name}__date__gte': month_start})