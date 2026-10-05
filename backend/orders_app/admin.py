"""Admin configuration for the orders app."""

from django.contrib import admin

from orders_app.models import Cancellation, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Edit order line items inline on the order page."""

    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Configure the order list and detail view in the admin."""

    list_display = ("id", "sold_at", "fulfillment_status", "buyer_name", "ship_city", "tracking_number", "ebay_order_id")
    list_filter = ("fulfillment_status",)
    search_fields = ("buyer_name", "ebay_username", "tracking_number", "ebay_order_id")
    date_hierarchy = "sold_at"
    inlines = [OrderItemInline]


@admin.register(Cancellation)
class CancellationAdmin(admin.ModelAdmin):
    """Show why and from where orders were cancelled."""

    list_display = ("order", "source", "item_action", "created_at")
    list_filter = ("source",)
