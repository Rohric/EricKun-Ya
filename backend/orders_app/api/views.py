"""API views for the orders app."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from orders_app.models import Order

from .serializers import OrderSerializer


class OrderList(generics.ListCreateAPIView):
    """List all orders or create a new one with its items."""

    queryset = Order.objects.all().prefetch_related("items")
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]


class OrderDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single order."""

    queryset = Order.objects.all().prefetch_related("items")
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
