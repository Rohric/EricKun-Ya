"""Detailed sales reports: one row per sold position, and breakdowns by channel or category."""

from decimal import Decimal

from django.db.models import Q

from finance_app.models import FinanceSettings
from finance_app.services import counted_items, estimated_fee

CHANNEL_LABELS = {"ebay": "eBay", "manual": "Manuell"}
NO_CATEGORY = "Ohne Kategorie"
MISSING_PRODUCT = "(Artikel nicht mehr vorhanden)"
ZERO = Decimal("0")
MONEY_FIELDS = ("revenue", "fee", "profit")


def sales_report(start, end, category=None, channel=None):
    """Return the paid, non-cancelled sales of a period as rows plus their totals."""
    rate = FinanceSettings.load().ebay_fee_rate
    rows = [_row(item, rate) for item in _report_items(start, end, category, channel)]
    return {"rows": rows, "totals": _totals(rows), "fee_rate": rate}


def breakdown(start, end, by):
    """Group the period's sales by "channel" or "category" and sum revenue, fees and profit."""
    grouped = {}
    for row in sales_report(start, end)["rows"]:
        key = row["channel"] if by == "channel" else row["category_group"]
        grouped.setdefault(key, []).append(row)
    groups = [{"key": key, "label": CHANNEL_LABELS.get(key, key), **_totals(rows)} for key, rows in grouped.items()]
    return sorted(groups, key=lambda group: group["revenue"], reverse=True)


def _report_items(start, end, category, channel):
    """Return the period's line items, optionally narrowed to a category tree or a channel."""
    items = counted_items(start, end).select_related("order", "product__category__parent")
    if category:
        items = items.filter(Q(product__category_id=category) | Q(product__category__parent_id=category))
    if channel:
        items = items.filter(order__ebay_order_id__isnull=channel == "manual")
    return items.order_by("-order__sold_at", "-id")


def _row(item, rate):
    """Describe one sold position with its labels and amounts."""
    channel = "ebay" if item.order.ebay_order_id else "manual"
    return {
        "date": item.order.sold_at,
        "order": item.order_id,
        "channel": channel,
        "channel_label": CHANNEL_LABELS[channel],
        **_product_labels(item.product),
        **_amounts(item, item.product, channel, rate),
    }


def _product_labels(product):
    """Return the columns that describe the sold product (placeholders if it was deleted)."""
    return {
        "title": product.title if product else MISSING_PRODUCT,
        "sku": product.sku if product else "",
        "category": product.category_path if product else "",
        "category_group": _category_group(product),
    }


def _amounts(item, product, channel, rate):
    """Return the money columns; without the product its cost is unknown, so fee and profit are 0."""
    revenue = item.sold_price * item.quantity
    fee = estimated_fee(revenue, rate) if product and channel == "ebay" else ZERO
    profit = revenue - product.purchase_price * item.quantity - fee if product else ZERO
    return {
        "quantity": item.quantity,
        "purchase_price": product.purchase_price if product else None,
        "sold_price": item.sold_price,
        "revenue": revenue,
        "fee": fee,
        "profit": profit,
        "margin": _margin(profit, revenue),
    }


def _category_group(product):
    """Return the name of the product's top-level category."""
    if product is None or product.category is None:
        return NO_CATEGORY
    return (product.category.parent or product.category).name


def _margin(profit, revenue):
    """Return the profit as a percentage of the revenue, or None without revenue."""
    if not revenue:
        return None
    return (profit / revenue * Decimal("100")).quantize(Decimal("0.1"))


def _totals(rows):
    """Sum positions, units and amounts of the rows and derive the overall margin."""
    totals = {field: sum((row[field] for row in rows), ZERO) for field in MONEY_FIELDS}
    totals["positions"] = len(rows)
    totals["quantity"] = sum(row["quantity"] for row in rows)
    totals["margin"] = _margin(totals["profit"], totals["revenue"])
    return totals
