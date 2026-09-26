"""Helpers for the products app."""

import uuid

from products_app.models import Product

SKU_PREFIX = "ART"


def generate_sku():
    """Return a unique SKU built from a short random hex suffix."""
    while True:
        candidate = f"{SKU_PREFIX}-{uuid.uuid4().hex[:8].upper()}"
        if not Product.objects.filter(sku=candidate).exists():
            return candidate
