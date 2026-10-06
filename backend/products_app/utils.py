"""Helpers for the products app: SKU generation, list filters and status counts."""

import uuid

from django.db.models import Count, Q
from rest_framework.exceptions import ValidationError

from products_app.models import Product

SKU_PREFIX = "ART"
BAD_STATUS = "Unbekannter Status. Erlaubt: available, reserved, sold, archived."
BAD_CATEGORY = "Die Kategorie muss eine Zahl sein."


def generate_sku():
    """Return a unique SKU built from a short random hex suffix."""
    while True:
        candidate = f"{SKU_PREFIX}-{uuid.uuid4().hex[:8].upper()}"
        if not Product.objects.filter(sku=candidate).exists():
            return candidate


def filter_products(queryset, params):
    """Narrow products by the optional ?status=, ?category= and ?search= parameters."""
    queryset = _by_category(queryset, params.get("category"))
    queryset = _by_search(queryset, params.get("search"))
    return _by_status(queryset, params.get("status"))


def status_counts(params):
    """Return the number of products per status (plus "all") for the category/search filters."""
    products = _by_search(_by_category(Product.objects.all(), params.get("category")), params.get("search"))
    found = dict(products.values_list("status").annotate(total=Count("id")))
    counts = {status: found.get(status, 0) for status in Product.Status.values}
    counts["all"] = sum(counts.values())
    return counts


def _by_status(queryset, status):
    """Filter by one product status; an unknown value is a client error."""
    if not status:
        return queryset
    if status not in Product.Status.values:
        raise ValidationError(BAD_STATUS)
    return queryset.filter(status=status)


def _by_category(queryset, category):
    """Filter by a category id, including the products of its sub-categories."""
    if not category:
        return queryset
    if not str(category).isdigit():
        raise ValidationError(BAD_CATEGORY)
    return queryset.filter(Q(category_id=category) | Q(category__parent_id=category))


def _by_search(queryset, text):
    """Filter by a text that must occur in the title or the SKU."""
    text = (text or "").strip()
    if not text:
        return queryset
    return queryset.filter(Q(title__icontains=text) | Q(sku__icontains=text))
