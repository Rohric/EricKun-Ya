"""API views for the orders app."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders_app import services
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

    def perform_destroy(self, instance):
        """Restock the items before deleting the order."""
        services.sync_stock(instance, sign=1)
        instance.delete()


class OrderCancelView(APIView):
    """Cancel an order: restock its items and apply the chosen product action."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Cancel the order; body 'item_action' = available | archive | delete."""
        order = generics.get_object_or_404(Order, pk=pk)
        services.cancel_order(order, request.data.get("item_action", "available"))
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)
