from django import template
from django.utils import timezone
from datetime import datetime

register = template.Library()


def _to_dt(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return None
    try:
        if timezone.is_aware(value):
            value = timezone.localtime(value)
    except Exception:
        pass
    return value


@register.filter
def custom_date(value):
    """Format date as 'Sep 22, 2025 10:38'"""
    dt = _to_dt(value)
    if not dt:
        return ''
    return dt.strftime('%b %d, %Y %H:%M')


@register.filter
def custom_date_only(value):
    """Format date as 'Sep 22, 2025'"""
    dt = _to_dt(value)
    if not dt:
        return ''
    return dt.strftime('%b %d, %Y')


@register.filter(name='date_medium')
def date_medium(value):
    """Medium date format used across templates: 'Sep 22, 2025 10:38'"""
    dt = _to_dt(value)
    if not dt:
        return ''
    return dt.strftime('%b %d, %Y %H:%M')
