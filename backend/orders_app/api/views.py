"""API views for the orders app."""

from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import OptionalPagePagination
from orders_app import services
from orders_app.models import Order

from .serializers import CancelSerializer, OrderSerializer


def _order_queryset():
    """Return orders with items, products and cancellation preloaded (avoids N+1 queries)."""
    return (
        Order.objects.select_related("cancellation")
        .prefetch_related("items__product")
        .order_by("-sold_at", "-id")
    )


class OrderList(generics.ListCreateAPIView):
    """
    List and create orders.

    - GET: newest first; ?page=N enables pagination.
    - POST: create an order with its items and book the stock.
    """

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagePagination

    def get_queryset(self):
        """Return orders with their related data preloaded."""
        return _order_queryset()


class OrderDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single order."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return orders with their related data preloaded."""
        return _order_queryset()

    @transaction.atomic
    def perform_destroy(self, instance):
        """Restock the items and delete the order in one transaction."""
        services.sync_stock(instance, sign=1)
        instance.delete()


class OrderCancelView(APIView):
    """Cancel an order: restock its items, record the reason, apply the product action."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Cancel the order; body 'item_action' = available | archive | delete, optional 'reason'."""
        order = generics.get_object_or_404(Order, pk=pk)
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_order(order, **serializer.validated_data)
        return Response(OrderSerializer(_order_queryset().get(pk=pk)).data)
