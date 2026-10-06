"""Aggregate the eBay connection and setup state for the eBay tab."""

from collections import Counter

from django.conf import settings

from ebay_app import client
from ebay_app.models import EbayAccount, EbayListing, EbayLocation


def connection_status():
    """Return connection, setup and readiness flags for the frontend checklist."""
    account = EbayAccount.load()
    location = EbayLocation.objects.select_related("warehouse").filter(warehouse__is_default=True).first()
    location_ok = bool(location) and not location.needs_resync
    return {
        "environment": settings.EBAY_ENV,
        "missing_settings": client.missing_settings(),
        "connected": account.is_connected,
        "refresh_expires_at": account.refresh_expires_at,
        "policies_ready": account.has_policies,
        "location": _location_info(location),
        "ready": account.is_connected and account.has_policies and location_ok,
        "orders_synced_at": account.orders_synced_at,
        "listings": listing_counts(),
    }


def listing_counts():
    """Count the listings per displayed state (online, changed, ended, draft, error)."""
    states = Counter(listing.state for listing in EbayListing.objects.select_related("product"))
    return {state: states.get(state, 0) for state in ("online", "changed", "ended", "draft", "error")}


def _location_info(location):
    """Return the transferred default location, or None."""
    if location is None:
        return None
    return {
        "key": location.merchant_location_key,
        "warehouse": str(location.warehouse),
        "last_synced": location.last_synced,
        "needs_resync": location.needs_resync,
    }
