import os
import base64
import json
import os
from urllib import request, parse, error


def _post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[bool, str]:
    data = json.dumps(payload).encode('utf-8')
    req = request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            return 200 <= resp.status < 300, body
    except Exception as e:
        return False, str(e)


def send_sms(phone: str, message: str) -> tuple[bool, str]:
    """Send an SMS using either Zapier Catch Hook or Twilio REST API based on env configuration.
    Returns (success, info).
    Environment options:
      - ZAPIER_SMS_WEBHOOK_URL: If set, POSTs JSON {phone, message}
      - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM: If set, send via Twilio API
    """
    phone = (phone or '').strip()
    if not phone or not message:
        return False, "Missing phone or message"

    zapier_url = os.getenv('ZAPIER_SMS_WEBHOOK_URL')
    if zapier_url:
        ok, info = _post_json(zapier_url, {"phone": phone, "message": message})
        return ok, info

    # Twilio fallback via HTTP API
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    from_num = os.getenv('TWILIO_FROM')
    if sid and token and from_num:
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = parse.urlencode({
            'To': phone,
            'From': from_num,
            'Body': message,
        }).encode('utf-8')
        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        req = request.Request(twilio_url, data=data, headers={'Authorization': f'Basic {auth}'})
        try:
            with request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode('utf-8')
                return 200 <= resp.status < 300, body
        except Exception as e:
            return False, str(e)

    return False, "No SMS provider configured. Set ZAPIER_SMS_WEBHOOK_URL or Twilio env vars."


from django.core.cache import cache
from django.utils import timezone

def add_audit_log(user=None, action: str | None = None, details: str | None = None, **kwargs) -> None:
    """Record an audit entry in cache.
    Accepts flexible arguments:
      - action or action_type
      - details or description
      - ip (optional)
      - any extra metadata via kwargs stored under 'meta'
    """
    try:
        logs = cache.get('audit_logs', []) or []
        action_val = action or kwargs.pop('action_type', None) or ''
        description_val = (kwargs.pop('description', None) or details or '')
        ip = kwargs.pop('ip', None)
        # Remaining kwargs are metadata
        meta = {k: v for k, v in kwargs.items() if v is not None}
        entry = {
            'timestamp': timezone.localtime().strftime('%Y-%m-%d %H:%M:%S'),
            'user': getattr(user, 'username', str(user) if user else 'system'),
            'action': action_val,
            'description': description_val,
        }
        if ip:
            entry['ip'] = ip
        if meta:
            entry['meta'] = meta
        logs.append(entry)
        logs = logs[-500:]
        cache.set('audit_logs', logs, None)
    except Exception:
        pass

def get_audit_logs() -> list:
    logs = cache.get('audit_logs', []) or []
    return list(reversed(logs))

def clear_audit_logs() -> None:
    cache.delete('audit_logs')

def clear_inventory_cache(name: str | None = None, brand: str | None = None) -> None:
    try:
        cache.delete('api_inv_items_v1')
        cache.delete('dashboard_metrics_v1')
        if name:
            cache.delete(f'api_inv_brands_{name}')
            # Invalidate stock caches for specific brand, unbranded alias, and any-brand aggregate
            keys = {f"api_inv_stock_{name}_{brand or 'any'}", f"api_inv_stock_{name}_any"}
            if (brand or '').lower() == 'unbranded' or not (brand or '').strip():
                keys.add(f"api_inv_stock_{name}_any")
            for k in keys:
                cache.delete(k)
    except Exception:
        pass


def adjust_inventory(name: str, brand: str, qty_delta: int) -> tuple[bool, str, int | None]:
    """Adjust inventory by name+brand with qty_delta (negative to deduct, positive to restock).
    Returns (ok, status, remaining_qty). status in {ok, not_found, invalid}.
    """
    try:
        from .models import InventoryItem
        name = (name or '').strip()
        brand = (brand or '').strip()
        if not name:
            return False, 'invalid', None
        # Resolve by brand name (case-insensitive)
        item = InventoryItem.objects.filter(name=name, brand__name__iexact=brand).first()
        if not item:
            return False, 'not_found', None
        new_qty = item.quantity + int(qty_delta)
        if new_qty < 0:
            new_qty = 0
        item.quantity = new_qty
        item.save()
        clear_inventory_cache(name, brand)
        return True, 'ok', new_qty
    except Exception as e:
        return False, str(e), None
