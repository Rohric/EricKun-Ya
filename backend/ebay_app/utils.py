"""Small helpers shared by the eBay services."""

from decimal import Decimal, InvalidOperation


def to_decimal(value):
    """Return an amount eBay sent as text as Decimal, or None if it is missing or unreadable."""
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None
