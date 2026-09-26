"""Serializers for the products app."""

from rest_framework import serializers

from products_app.models import Product


class ProductSerializer(serializers.ModelSerializer):
    """Serialize product data and expose the computed profit read-only."""

    profit = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "title", "description", "condition",
            "purchase_price", "sale_price", "quantity", "aspects",
            "purchase_date", "profit", "created_at", "updated_at",
        ]
        read_only_fields = ["sku", "created_at", "updated_at"]
