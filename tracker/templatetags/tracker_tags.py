from decimal import Decimal
from django import template

register = template.Library()

@register.filter(name='currency')
def currency(value):
    """Formats numeric value as Indian Rupee string, e.g. ₹5,000.00"""
    if value is None or value == '':
        return '₹0.00'
    try:
        dec_val = Decimal(str(value))
        return f"₹{dec_val:,.2f}"
    except (ValueError, TypeError):
        return f"₹{value}"

@register.filter(name='sub')
def sub(value, arg):
    """Subtracts the arg from value."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (ValueError, TypeError):
        return Decimal('0.00')

@register.filter(name='abs_val')
def abs_val(value):
    """Returns absolute value."""
    try:
        return abs(Decimal(str(value)))
    except (ValueError, TypeError):
        return value
