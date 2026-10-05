"""Admin configuration for the eBay app (tokens stay hidden)."""

from django.contrib import admin

from ebay_app.models import EbayAccount, EbayImage, EbayListing, EbayLocation


@admin.register(EbayAccount)
class EbayAccountAdmin(admin.ModelAdmin):
    """Show connection state and policy ids; the encrypted tokens are never displayed."""

    list_display = ("__str__", "connected_at", "refresh_expires_at", "has_policies")
    exclude = ("access_token", "refresh_token", "oauth_state")
    readonly_fields = ("access_expires_at", "refresh_expires_at", "connected_at", "oauth_state_created_at")


@admin.register(EbayLocation)
class EbayLocationAdmin(admin.ModelAdmin):
    """Show which warehouse is mirrored under which merchantLocationKey."""

    list_display = ("merchant_location_key", "warehouse", "last_synced")


@admin.register(EbayListing)
class EbayListingAdmin(admin.ModelAdmin):
    """Show each product's offer, listing id and sync state."""

    list_display = ("product", "status", "listing_id", "category_name", "last_synced", "sync_error")
    list_filter = ("status",)


@admin.register(EbayImage)
class EbayImageAdmin(admin.ModelAdmin):
    """Show which product images are already hosted by eBay."""

    list_display = ("source_name", "eps_url", "expires_at")
