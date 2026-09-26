"""Serializers for the products app."""

from rest_framework import serializers

from products_app.models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """Serialize a category with its optional parent and readable path."""

    path = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "parent", "path"]

    def get_path(self, obj):
        """Return the readable category path."""
        return str(obj)


class ProductImageSerializer(serializers.ModelSerializer):
    """Serialize a single product image."""

    class Meta:
        model = ProductImage
        fields = ["id", "image", "position"]


class ProductSerializer(serializers.ModelSerializer):
    """Serialize product data with computed profit and nested images (read-only)."""

    profit = serializers.ReadOnlyField()
    category_path = serializers.ReadOnlyField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "sku", "title", "description", "category", "category_path",
            "condition", "status", "purchase_price", "sale_price", "quantity",
            "aspects", "purchase_date", "profit", "images", "created_at", "updated_at",
        ]
        read_only_fields = ["sku", "created_at", "updated_at"]
