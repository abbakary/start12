from django import template

register = template.Library()

@register.filter
def has_group(user, name):
    try:
        return user.groups.filter(name=name).exists()
    except Exception:
        return False
