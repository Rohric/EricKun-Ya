"""Serializers for orders and their line items."""

from rest_framework import serializers

from orders_app.models import Order, OrderItem
from orders_app.services import sync_stock


class OrderItemSerializer(serializers.ModelSerializer):
    """Serialize a single order line item; product may be null if it was deleted."""

    subtotal = serializers.ReadOnlyField()
    profit = serializers.ReadOnlyField()
    product_title = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_title", "sold_price", "quantity", "subtotal", "profit"]

    def get_product_title(self, obj):
        """Return the product title, or a placeholder if the product was deleted."""
        return obj.product.title if obj.product_id else "(gelöschter Artikel)"


class OrderSerializer(serializers.ModelSerializer):
    """Serialize an order with buyer/shipping data and nested writable line items."""

    items = OrderItemSerializer(many=True)
    total_revenue = serializers.ReadOnlyField()
    total_profit = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id", "sold_at", "fulfillment_status", "tracking_number",
            "buyer_name", "ship_street", "ship_zip", "ship_city", "ship_country",
            "ebay_username", "reklamation_note",
            "items", "total_revenue", "total_profit", "created_at",
        ]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        """Create the order with its items and deduct the sold quantities from stock."""
        items = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        _create_items(order, items)
        sync_stock(order, sign=-1)
        return order

    def update(self, instance, validated_data):
        """Update the order; if items change, restock the old set and deduct the new."""
        items = validated_data.pop("items", None)
        if items is not None:
            sync_stock(instance, sign=1)
            instance.items.all().delete()
        instance = super().update(instance, validated_data)
        if items is not None:
            _create_items(instance, items)
            sync_stock(instance, sign=-1)
        return instance


def _create_items(order, items):
    """Bulk-create the given line items for an order."""
    OrderItem.objects.bulk_create(
        [OrderItem(order=order, **item) for item in items]
    )
