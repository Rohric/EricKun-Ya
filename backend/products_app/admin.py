"""Admin configuration for the products app."""

from django.contrib import admin

from products_app.models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Configure the category admin."""

    list_display = ("__str__", "parent")
    list_filter = ("parent",)
    search_fields = ("name",)


class ProductImageInline(admin.TabularInline):
    """Edit a product's images inline on the product page."""

    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Configure the product list and detail view in the admin."""

    list_display = ("sku", "title", "category", "status", "condition", "sale_price", "quantity", "updated_at")
    search_fields = ("sku", "title")
    list_filter = ("status", "condition", "category")
    readonly_fields = ("sku", "created_at", "updated_at")
    inlines = [ProductImageInline]
