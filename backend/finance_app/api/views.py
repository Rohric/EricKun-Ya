"""API views for the finance app: goals, settings and reports."""

from datetime import date

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance_app import services
from finance_app.models import FinanceSettings, Goal

from .serializers import (
    FinanceSettingsSerializer,
    GoalSerializer,
    ReportRangeSerializer,
    ReportYearSerializer,
)


class GoalList(generics.ListCreateAPIView):
    """List all goals or create a new one."""

    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]


class GoalDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single goal."""

    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]


class FinanceSettingsView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the singleton finance settings."""

    serializer_class = FinanceSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the singleton settings row."""
        return FinanceSettings.load()


class ProfitLossView(APIView):
    """Return revenue, expenses and the gross/reserve/net profit breakdown for a date range."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Compute the tax breakdown for ?from=&to= (ISO dates, default: this year)."""
        start, end = _parse_range(request)
        data = services.financial_summary(start, end)
        data.update({
            "from": start,
            "to": end,
            "tax_rate": FinanceSettings.load().tax_reserve_rate,
        })
        return Response(data)


class MonthlyRevenueView(APIView):
    """Return the twelve monthly revenue totals for a given year."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Compute monthly revenue for ?year= (defaults to the current year)."""
        params = ReportYearSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        year = params.validated_data.get("year", date.today().year)
        return Response({"year": year, "monthly_revenue": services.monthly_revenue(year)})


def _parse_range(request):
    """Return the validated (from, to) dates, defaulting to the current year so far."""
    params = ReportRangeSerializer(data=request.query_params)
    params.is_valid(raise_exception=True)
    today = date.today()
    start = params.validated_data.get("from", date(today.year, 1, 1))
    end = params.validated_data.get("to", today)
    return start, end
