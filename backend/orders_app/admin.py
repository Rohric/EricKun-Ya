"""Admin configuration for the orders app."""

from django.contrib import admin

from orders_app.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Edit order line items inline on the order page."""

    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Configure the order list and detail view in the admin."""

    list_display = ("id", "sold_at", "fulfillment_status", "tracking_number")
    list_filter = ("fulfillment_status",)
    date_hierarchy = "sold_at"
    inlines = [OrderItemInline]
