"""Serializers for orders and their line items."""

from rest_framework import serializers

from orders_app.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serialize a single order line item."""

    subtotal = serializers.ReadOnlyField()
    profit = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "sold_price", "quantity", "subtotal", "profit"]


class OrderSerializer(serializers.ModelSerializer):
    """Serialize an order together with its nested writable line items."""

    items = OrderItemSerializer(many=True)
    total_revenue = serializers.ReadOnlyField()
    total_profit = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id", "sold_at", "fulfillment_status", "tracking_number",
            "items", "total_revenue", "total_profit", "created_at",
        ]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        """Create the order and its line items in one request."""
        items = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        _create_items(order, items)
        return order

    def update(self, instance, validated_data):
        """Update the order and, if items are given, replace them."""
        items = validated_data.pop("items", None)
        instance = super().update(instance, validated_data)
        if items is not None:
            instance.items.all().delete()
            _create_items(instance, items)
        return instance


def _create_items(order, items):
    """Bulk-create the given line items for an order."""
    OrderItem.objects.bulk_create(
        [OrderItem(order=order, **item) for item in items]
    )
