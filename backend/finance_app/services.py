"""Business logic for financial reports, the tax breakdown and goal progress."""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from products_app.models import Product
from orders_app.models import OrderItem

from finance_app.models import FinanceSettings

_REVENUE_EXPR = ExpressionWrapper(
    F("sold_price") * F("quantity"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)
_PROFIT_EXPR = ExpressionWrapper(
    (F("sold_price") - F("product__purchase_price")) * F("quantity"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)


def _items_in_period(start, end):
    """Return order items whose order was sold within [start, end]."""
    return OrderItem.objects.filter(
        order__sold_at__date__gte=start,
        order__sold_at__date__lte=end,
    )


def revenue_for_period(start, end):
    """Return total revenue (sale prices) for the given date range."""
    total = _items_in_period(start, end).aggregate(s=Sum(_REVENUE_EXPR))["s"]
    return total or Decimal("0")


def profit_for_period(start, end):
    """Return total gross profit (sale minus purchase) for the given date range."""
    total = _items_in_period(start, end).aggregate(s=Sum(_PROFIT_EXPR))["s"]
    return total or Decimal("0")


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
        "expenses": purchase_expenses_for_period(start, end),
        "gross_profit": gross,
        "tax_reserve": reserve,
        "net_profit": gross - reserve,
    }


def _month_bounds(year, month):
    """Return the first and last day of the given month."""
    start = date(year, month, 1)
    if month == 12:
        return start, date(year, 12, 31)
    return start, date(year, month + 1, 1) - timedelta(days=1)


def monthly_revenue(year):
    """Return a list of 12 revenue totals, one per month of the year."""
    return [revenue_for_period(*_month_bounds(year, month)) for month in range(1, 13)]


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
