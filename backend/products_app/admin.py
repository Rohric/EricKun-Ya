"""Admin configuration for the products app."""

from django.contrib import admin

from products_app.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Configure the product list and detail view in the admin."""

    list_display = ("sku", "title", "condition", "sale_price", "quantity", "updated_at")
    search_fields = ("sku", "title")
    list_filter = ("condition",)
    readonly_fields = ("sku", "created_at", "updated_at")
