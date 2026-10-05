"""Serializers for orders and their line items."""

from collections import Counter

from django.db import transaction
from rest_framework import serializers

from orders_app.models import Cancellation, Order, OrderItem
from orders_app.services import sync_stock


class CancelSerializer(serializers.Serializer):
    """Validate what happens to the products and why an order is cancelled."""

    item_action = serializers.ChoiceField(
        choices=Cancellation.ItemAction.choices,
        default=Cancellation.ItemAction.AVAILABLE,
    )
    reason = serializers.CharField(allow_blank=True, default="", max_length=1000)


class CancellationSerializer(serializers.ModelSerializer):
    """Serialize the record of a cancelled order."""

    class Meta:
        model = Cancellation
        fields = ["reason", "source", "item_action", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    """Serialize a single order line item; product may be null if it was deleted."""

    subtotal = serializers.ReadOnlyField()
    profit = serializers.ReadOnlyField()
    product_title = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_title", "sold_price", "quantity", "subtotal", "profit"]
        extra_kwargs = {
            "product": {"required": True, "allow_null": False},
            "quantity": {"min_value": 1},
        }

    def get_product_title(self, obj):
        """Return the product title, or a placeholder if the product was deleted."""
        return obj.product.title if obj.product_id else "(gelöschter Artikel)"


class OrderSerializer(serializers.ModelSerializer):
    """Serialize an order with buyer/shipping data and nested writable line items."""

    items = OrderItemSerializer(many=True)
    total_revenue = serializers.ReadOnlyField()
    total_profit = serializers.ReadOnlyField()
    cancellation = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "sold_at", "fulfillment_status", "tracking_number", "shipping_carrier",
            "buyer_name", "ship_street", "ship_zip", "ship_city", "ship_country",
            "ebay_username", "ebay_order_id", "return_note", "cancellation",
            "items", "total_revenue", "total_profit", "created_at",
        ]
        read_only_fields = ["ebay_order_id", "created_at"]

    def get_cancellation(self, obj):
        """Return the cancellation record, or None for orders that were not cancelled."""
        cancellation = getattr(obj, "cancellation", None)
        return CancellationSerializer(cancellation).data if cancellation else None

    def validate(self, data):
        """Reject items that exceed the available stock of their product."""
        if "items" in data:
            _check_stock(data["items"], self.instance)
        return data

    @transaction.atomic
    def create(self, validated_data):
        """Create the order with its items and deduct the sold quantities from stock."""
        items = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        _create_items(order, items)
        sync_stock(order, sign=-1)
        return order

    @transaction.atomic
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


def _check_stock(items, order=None):
    """Raise a validation error if any product lacks enough stock for the items."""
    wanted = Counter()
    for item in items:
        wanted[item["product"]] += item["quantity"]
    booked = _booked_quantities(order)
    for product, amount in wanted.items():
        available = product.quantity + booked.get(product.pk, 0)
        if amount > available:
            raise serializers.ValidationError(
                f"Nur {available} Stück von „{product.title}“ verfügbar."
            )


def _booked_quantities(order):
    """Return {product_id: quantity} already booked by an existing order."""
    booked = Counter()
    if order is None:
        return booked
    for item in order.items.all():
        booked[item.product_id] += item.quantity
    return booked
