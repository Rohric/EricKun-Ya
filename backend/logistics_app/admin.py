"""Admin configuration for the logistics app."""

from django.contrib import admin

from logistics_app.models import Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    """Configure the warehouse admin."""

    list_display = ("name", "city", "country", "is_default", "updated_at")
    list_filter = ("is_default", "country")
