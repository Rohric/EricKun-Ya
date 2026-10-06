"""Key figures for the dashboard's area tiles, gathered from the domain apps."""

from django.db.models import Sum
from django.utils import timezone

from finance_app.services import profit_for_period, revenue_for_period
from orders_app.models import Order
from products_app.models import Product

WAITING_STATES = (Order.Fulfillment.OPEN, Order.Fulfillment.PACKED)
SELLABLE_STATES = (Product.Status.AVAILABLE, Product.Status.RESERVED)


def dashboard_summary():
    """Return the figures shown on the orders, finance and stock tiles."""
    return {"orders": _order_figures(), "finance": _finance_figures(), "stock": _stock_figures()}


def _order_figures():
    """Count orders that still have to be shipped, and those in a return."""
    waiting = Order.objects.filter(fulfillment_status__in=WAITING_STATES)
    return {
        "to_ship": waiting.count(),
        "unpaid": waiting.filter(payment_status=Order.Payment.PENDING).count(),
        "in_return": Order.objects.filter(fulfillment_status=Order.Fulfillment.IN_RETURN).count(),
    }


def _finance_figures():
    """Return revenue and gross profit of the current month."""
    today = timezone.localdate()
    start = today.replace(day=1)
    return {"revenue_month": revenue_for_period(start, today), "profit_month": profit_for_period(start, today)}


def _stock_figures():
    """Count the sellable products and the units they hold."""
    sellable = Product.objects.filter(status__in=SELLABLE_STATES)
    return {"products": sellable.count(), "units": sellable.aggregate(total=Sum("quantity"))["total"] or 0}
