"""Aggregate the eBay connection and setup state for the eBay tab."""

from collections import Counter

from django.conf import settings

from ebay_app import client
from ebay_app.models import EbayAccount, EbayListing, EbayLocation

COUNTED_STATES = ("online", "changed", "ended", "draft", "error", "unassigned")


def connection_status():
    """Return connection, setup and readiness flags for the frontend checklist."""
    account, location = EbayAccount.load(), _default_location()
    return {
        "environment": settings.EBAY_ENV,
        "missing_settings": client.missing_settings(),
        "connected": account.is_connected,
        "refresh_expires_at": account.refresh_expires_at,
        "policies_ready": account.has_policies,
        "location": _location_info(location),
        "ready": _is_ready(account, location),
        "orders_synced_at": account.orders_synced_at,
        "listings": _listing_counts(),
    }


def _default_location():
    """Return the eBay location of the default warehouse, or None if it was never transferred."""
    return EbayLocation.objects.select_related("warehouse").filter(warehouse__is_default=True).first()


def _is_ready(account, location):
    """Return True once the seller is connected, has policies and an up-to-date location."""
    location_ok = bool(location) and not location.needs_resync
    return account.is_connected and account.has_policies and location_ok


def _listing_counts():
    """Count the listings per displayed state; "unassigned" are the ones waiting for an article."""
    states = Counter(listing.state for listing in EbayListing.objects.select_related("product"))
    return {state: states.get(state, 0) for state in COUNTED_STATES}


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
