"""Helpers for the products app: internal article numbers, list filters and status counts."""

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from rest_framework.exceptions import ValidationError

from products_app.models import Product, SkuSequence

SKU_DIGITS = 6  # EK-000123
BAD_STATUS = "Unbekannter Status. Erlaubt: available, reserved, sold, archived."
BAD_CATEGORY = "Die Kategorie muss eine Zahl sein."


@transaction.atomic
def generate_sku():
    """Return the next internal article number (e.g. EK-000123); none is ever handed out twice."""
    sequence, _ = SkuSequence.objects.select_for_update().get_or_create(pk=1)
    sequence.last_number += 1
    while Product.objects.filter(sku=_format_sku(sequence.last_number)).exists():
        sequence.last_number += 1  # skip a number that came in from outside, e.g. with an old listing
    sequence.save()
    return _format_sku(sequence.last_number)


def _format_sku(number):
    """Return the article number for a counter value: prefix, dash, zero-padded number."""
    return f"{settings.SKU_PREFIX}-{number:0{SKU_DIGITS}d}"


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
