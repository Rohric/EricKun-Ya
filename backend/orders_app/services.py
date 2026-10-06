"""Business logic for orders: list filters, stock synchronisation and cancellation."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from orders_app.models import Cancellation, Order, OrderItem
from products_app.models import Product

SOURCES = ("ebay", "manual")
BAD_SOURCE = "Unbekannte Herkunft. Erlaubt: ebay, manual."
BAD_PAYMENT = "Unbekannter Zahlungsstatus. Erlaubt: paid, pending."
BAD_STATUS = "Unbekannter Bestellstatus."
BAD_PRODUCTS = "„products“ muss eine kommagetrennte Liste von Artikel-IDs sein."
ALREADY_CANCELLED = "Diese Bestellung ist bereits storniert."


def parse_product_ids(raw):
    """Turn "1,2,3" into a list of ids; an empty value means all products."""
    parts = [part.strip() for part in (raw or "").split(",") if part.strip()]
    if not all(part.isdigit() for part in parts):
        raise ValidationError(BAD_PRODUCTS)
    return [int(part) for part in parts]


def product_sales(product_ids=None):
    """Return {product id: {"sold": units, "sales": [...]}} from all non-cancelled orders."""
    items = OrderItem.objects.filter(product__isnull=False).select_related("order")
    items = items.exclude(order__fulfillment_status=Order.Fulfillment.CANCELLED)
    if product_ids:
        items = items.filter(product_id__in=product_ids)
    result = {}
    for item in items.order_by("-order__sold_at", "-id"):
        entry = result.setdefault(str(item.product_id), {"sold": 0, "sales": []})
        entry["sold"] += item.quantity
        entry["sales"].append(_sale_entry(item))
    return result


def _sale_entry(item):
    """Describe one sold position of a product for the article page."""
    order = item.order
    return {
        "order": order.pk,
        "sold_at": order.sold_at,
        "quantity": item.quantity,
        "sold_price": item.sold_price,
        "fulfillment_status": order.fulfillment_status,
        "payment_status": order.payment_status,
        "source": "ebay" if order.ebay_order_id else "manual",
        "buyer_name": order.buyer_name,
    }


def filter_orders(queryset, params):
    """Narrow orders by the optional ?source=, ?payment= and ?status= parameters."""
    queryset = _by_source(queryset, params.get("source"))
    queryset = _by_choice(queryset, "payment_status", params.get("payment"), Order.Payment.values, BAD_PAYMENT)
    return _by_choice(queryset, "fulfillment_status", params.get("status"), Order.Fulfillment.values, BAD_STATUS)


def _by_source(queryset, source):
    """Keep orders that came from eBay, or the manually entered ones."""
    if not source:
        return queryset
    if source not in SOURCES:
        raise ValidationError(BAD_SOURCE)
    return queryset.filter(ebay_order_id__isnull=source == "manual")


def _by_choice(queryset, field, value, allowed, message):
    """Filter a choice field by an optional value; an unknown value is a client error."""
    if not value:
        return queryset
    if value not in allowed:
        raise ValidationError(message)
    return queryset.filter(**{field: value})


def _apply_stock_change(product, delta):
    """Adjust a product's stock by delta and keep its sale status in sync."""
    if product is None:
        return
    product.quantity = max(product.quantity + delta, 0)
    if product.quantity == 0 and product.status in (Product.Status.AVAILABLE, Product.Status.RESERVED):
        product.status = Product.Status.SOLD
    elif product.quantity > 0 and product.status == Product.Status.SOLD:
        product.status = Product.Status.AVAILABLE
    product.save(update_fields=["quantity", "status"])


def sync_stock(order, sign):
    """Apply (sign × quantity) to the stock of every line item's product."""
    for item in order.items.select_related("product"):
        _apply_stock_change(item.product, sign * item.quantity)


@transaction.atomic
def cancel_order(order, item_action, reason="", source=Cancellation.Source.MANUAL):
    """Cancel an order, restock its items, record why and apply the chosen product action."""
    if order.fulfillment_status == order.Fulfillment.CANCELLED:
        raise ValidationError(ALREADY_CANCELLED)  # a second run would restock the items twice
    sync_stock(order, sign=1)
    order.fulfillment_status = order.Fulfillment.CANCELLED
    order.save(update_fields=["fulfillment_status"])
    defaults = {"reason": reason, "source": source, "item_action": item_action}
    Cancellation.objects.update_or_create(order=order, defaults=defaults)
    _apply_item_action(order, item_action)


def _apply_item_action(order, item_action):
    """Set each product available/archived, or delete it, after a cancellation."""
    for item in order.items.select_related("product"):
        if item.product is None:
            continue
        if item_action == Cancellation.ItemAction.DELETE:
            item.product.delete()
        elif item_action == Cancellation.ItemAction.ARCHIVE:
            _set_status(item.product, Product.Status.ARCHIVED)
        else:
            _set_status(item.product, Product.Status.AVAILABLE)


def _set_status(product, status):
    """Persist a single product's status."""
    product.status = status
    product.save(update_fields=["status"])
