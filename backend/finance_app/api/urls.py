"""URL patterns for the finance app."""

from django.urls import path

from .views import (
    BreakdownView,
    FinanceSettingsView,
    GoalDetail,
    GoalList,
    MonthlyRevenueView,
    ProfitLossView,
    SalesReportView,
)

urlpatterns = [
    path("goals/", GoalList.as_view(), name="goal-list"),
    path("goals/<int:pk>/", GoalDetail.as_view(), name="goal-detail"),
    path("finance/settings/", FinanceSettingsView.as_view(), name="finance-settings"),
    path("finance/reports/profit-loss/", ProfitLossView.as_view(), name="finance-profit-loss"),
    path("finance/reports/monthly-revenue/", MonthlyRevenueView.as_view(), name="finance-monthly-revenue"),
    path("finance/reports/sales/", SalesReportView.as_view(), name="finance-sales-report"),
    path("finance/reports/breakdown/", BreakdownView.as_view(), name="finance-breakdown"),
]
