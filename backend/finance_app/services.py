"""Business logic for financial reports, the tax breakdown and goal progress."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from finance_app.models import FinanceSettings
from orders_app.models import Order, OrderItem
from products_app.models import Product

_REVENUE_EXPR = ExpressionWrapper(
    F("sold_price") * F("quantity"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)
_PROFIT_EXPR = ExpressionWrapper(
    (F("sold_price") - F("product__purchase_price")) * F("quantity"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)


def _day_bounds(start, end):
    """Return aware datetimes [start 00:00, end+1 00:00) so the sold_at index is usable."""
    tz = timezone.get_current_timezone()
    lower = timezone.make_aware(datetime.combine(start, time.min), tz)
    upper = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)
    return lower, upper


def _sold_items(start, end):
    """Return line items of non-cancelled orders sold within [start, end], paid or not."""
    lower, upper = _day_bounds(start, end)
    return OrderItem.objects.filter(
        order__sold_at__gte=lower,
        order__sold_at__lt=upper,
    ).exclude(order__fulfillment_status=Order.Fulfillment.CANCELLED)


def counted_items(start, end):
    """Return the line items that count as revenue: not cancelled and already paid."""
    return _sold_items(start, end).filter(order__payment_status=Order.Payment.PAID)


def revenue_for_period(start, end):
    """Return total revenue (sale prices) for the given date range."""
    total = counted_items(start, end).aggregate(s=Sum(_REVENUE_EXPR))["s"]
    return total or Decimal("0")


def pending_revenue_for_period(start, end):
    """Return the revenue of orders whose payment is still open (not counted as revenue yet)."""
    pending = _sold_items(start, end).filter(order__payment_status=Order.Payment.PENDING)
    return pending.aggregate(s=Sum(_REVENUE_EXPR))["s"] or Decimal("0")


def estimated_fee(revenue, rate=None):
    """Return the estimated eBay fee for a revenue amount (rate in percent)."""
    rate = FinanceSettings.load().ebay_fee_rate if rate is None else rate
    return (revenue * rate / Decimal("100")).quantize(Decimal("0.01"))


def estimated_fees_for_period(start, end):
    """Return the estimated eBay fees on the period's eBay sales of known products."""
    ebay_items = counted_items(start, end).filter(order__ebay_order_id__isnull=False, product__isnull=False)
    return estimated_fee(ebay_items.aggregate(s=Sum(_REVENUE_EXPR))["s"] or Decimal("0"))


def profit_for_period(start, end):
    """Return total gross profit (sale minus purchase minus estimated eBay fees) for the range."""
    total = counted_items(start, end).aggregate(s=Sum(_PROFIT_EXPR))["s"] or Decimal("0")
    return total - estimated_fees_for_period(start, end)


def purchase_expenses_for_period(start, end):
    """Return total spending on stock bought within the date range."""
    total = Product.objects.filter(
        purchase_date__gte=start, purchase_date__lte=end,
    ).aggregate(s=Sum("purchase_price"))["s"]
    return total or Decimal("0")


def tax_reserve(profit):
    """Return the suggested tax reserve for a profit amount."""
    rate = FinanceSettings.load().tax_reserve_rate
    return (profit * rate / Decimal("100")).quantize(Decimal("0.01"))


def financial_summary(start, end):
    """Return revenue, expenses and the gross/reserve/net profit breakdown for a period."""
    gross = profit_for_period(start, end)
    reserve = tax_reserve(gross)
    return {
        "revenue": revenue_for_period(start, end),
        "pending_revenue": pending_revenue_for_period(start, end),
        "expenses": purchase_expenses_for_period(start, end),
        "estimated_fees": estimated_fees_for_period(start, end),
        "gross_profit": gross,
        "tax_reserve": reserve,
        "net_profit": gross - reserve,
    }


def monthly_revenue(year):
    """Return 12 revenue totals (one per month) using a single grouped query."""
    rows = (
        counted_items(date(year, 1, 1), date(year, 12, 31))
        .annotate(month=TruncMonth("order__sold_at"))
        .values("month")
        .annotate(total=Sum(_REVENUE_EXPR))
    )
    totals = {row["month"].month: row["total"] for row in rows}
    return [totals.get(month, Decimal("0")) for month in range(1, 13)]


def _goal_bounds(goal):
    """Return the date range a goal is measured over (end falls back to today)."""
    return goal.start_date, goal.end_date or date.today()


def _percent(current, target):
    """Return current as a percent of target, guarding against zero."""
    if not target:
        return Decimal("0")
    return (current / target * Decimal("100")).quantize(Decimal("0.1"))


def goal_progress(goal):
    """Return the current amount and percent achieved for a goal."""
    start, end = _goal_bounds(goal)
    calc = revenue_for_period if goal.metric == goal.Metric.REVENUE else profit_for_period
    current = calc(start, end)
    return {"current": current, "target": goal.target_amount, "percent": _percent(current, goal.target_amount)}
