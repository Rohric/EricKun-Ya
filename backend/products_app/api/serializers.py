"""Serializers for the products app."""

from rest_framework import serializers

from products_app.models import Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """Serialize a single product image."""

    class Meta:
        model = ProductImage
        fields = ["id", "image", "position"]


class ProductSerializer(serializers.ModelSerializer):
    """Serialize product data with computed profit and nested images (read-only)."""

    profit = serializers.ReadOnlyField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "sku", "title", "description", "condition",
            "purchase_price", "sale_price", "quantity", "aspects",
            "purchase_date", "profit", "images", "created_at", "updated_at",
        ]
        read_only_fields = ["sku", "created_at", "updated_at"]
