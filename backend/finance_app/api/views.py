"""API views for the finance app: goals, settings and reports."""

from datetime import date

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance_app import services
from finance_app.models import FinanceSettings, Goal

from .serializers import FinanceSettingsSerializer, GoalSerializer


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
        """Compute the tax breakdown for ?from=&to= (ISO dates)."""
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
        year = int(request.query_params.get("year", date.today().year))
        return Response({"year": year, "monthly_revenue": services.monthly_revenue(year)})


def _parse_range(request):
    """Return (from, to) dates from query params, defaulting to this year."""
    today = date.today()
    start = request.query_params.get("from") or date(today.year, 1, 1).isoformat()
    end = request.query_params.get("to") or today.isoformat()
    return date.fromisoformat(start), date.fromisoformat(end)
