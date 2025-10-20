from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from .utils import add_audit_log


def _client_ip(request):
    try:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    except Exception:
        return None

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    ip = _client_ip(request)
    ua = (request.META.get('HTTP_USER_AGENT') or '')[:200]
    add_audit_log(user, 'login', f'Login at {timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")} from {ip or "?"} UA: {ua}')

@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    ip = _client_ip(request)
    ua = (request.META.get('HTTP_USER_AGENT') or '')[:200]
    add_audit_log(user, 'logout', f'Logout at {timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")} from {ip or "?"} UA: {ua}')

@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    username = (credentials or {}).get('username') or 'unknown'
    ip = _client_ip(request) if request else None
    ua = (request.META.get('HTTP_USER_AGENT') if request else '') or ''
    ua = ua[:200]
    add_audit_log(None, 'login_failed', f'Username: {username} from {ip or "?"} UA: {ua}')
