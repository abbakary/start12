from django import template
from django.contrib.auth.models import Group
from django.templatetags.static import static

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    try:
        group = Group.objects.get(name=group_name)
        return group in user.groups.all()
    except Group.DoesNotExist:
        return False

@register.simple_tag
def user_avatar(user):
    """Return user profile photo URL or default static avatar"""
    try:
        p = getattr(user, 'profile', None)
        if p and getattr(p, 'photo', None):
            if p.photo:
                return p.photo.url
    except Exception:
        pass
    return static('assets/images/dashboard/profile.png')
