from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    try:
        return field.as_widget(attrs={**field.field.widget.attrs, 'class': ((field.field.widget.attrs.get('class','') + ' ' + css).strip())})
    except Exception:
        return field
