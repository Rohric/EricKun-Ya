"""API views for the logistics app."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from logistics_app.models import Warehouse

from .serializers import WarehouseSerializer


class WarehouseList(generics.ListCreateAPIView):
    """List all warehouses (default first) or create a new one."""

    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]


class WarehouseDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single warehouse."""

    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
