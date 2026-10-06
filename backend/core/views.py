"""Project-level API views that span several apps."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.dashboard import dashboard_summary


class DashboardSummaryView(APIView):
    """Return the key figures for the dashboard's area tiles."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return order, finance and stock figures."""
        return Response(dashboard_summary())
