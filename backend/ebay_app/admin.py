"""Admin configuration for the eBay app (tokens stay hidden)."""

from django.contrib import admin

from ebay_app.models import (
    EbayAccount,
    EbayCategoryMapping,
    EbayImage,
    EbayListing,
    EbayLocation,
    EbayShippingProfile,
)


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
    """Show each listing with its eBay number, its article (if assigned) and its sync state."""

    list_display = ("sku", "product", "status", "listing_id", "title", "last_synced", "sync_error")
    list_filter = ("status", "needs_migration", "ignored")


@admin.register(EbayShippingProfile)
class EbayShippingProfileAdmin(admin.ModelAdmin):
    """Show the shipping profiles and the eBay policy each one stands for."""

    list_display = ("name", "shipping_service", "shipping_cost", "handling_days", "is_default", "policy_id")


@admin.register(EbayCategoryMapping)
class EbayCategoryMappingAdmin(admin.ModelAdmin):
    """Show which eBay category is remembered for which internal category."""

    list_display = ("category", "ebay_category_name", "ebay_category_id")


@admin.register(EbayImage)
class EbayImageAdmin(admin.ModelAdmin):
    """Show which product images are already hosted by eBay."""

    list_display = ("source_name", "eps_url", "expires_at")
