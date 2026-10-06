"""Read facts about online listings back from eBay: the price buyers see and the units sold."""

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException

from ebay_app import client
from ebay_app.models import EbayListing
from ebay_app.services.oauth import call, get_app_token

OFFER_PATH = "/sell/inventory/v1/offer"
BROWSE_ITEM = "/buy/browse/v1/item/get_item_by_legacy_id"


def refresh(listing):
    """Store eBay's sold quantity and the buyer-facing price of an online listing."""
    offer = call("GET", f"{OFFER_PATH}/{listing.offer_id}")
    listing.sold_quantity = (offer.get("listing") or {}).get("soldQuantity") or 0
    listing.ebay_price = _buyer_price(listing.listing_id)
    listing.facts_synced_at = timezone.now()
    listing.save(update_fields=["sold_quantity", "ebay_price", "facts_synced_at"])
    return listing


def refresh_quietly(listing):
    """Refresh the facts after a transfer; a failure must never undo a successful listing."""
    try:
        refresh(listing)
    except APIException:
        pass  # the facts stay as they were and can be refreshed by hand


def refresh_all():
    """Refresh every online listing and return how many succeeded and failed."""
    result = {"refreshed": 0, "failed": 0}
    for listing in EbayListing.objects.filter(status=EbayListing.Status.ONLINE).exclude(offer_id=""):
        try:
            refresh(listing)
            result["refreshed"] += 1
        except APIException:
            result["failed"] += 1
    return result


def _buyer_price(listing_id):
    """Return the price eBay shows to buyers, or None if the Browse API cannot tell (yet)."""
    if not listing_id:
        return None
    headers = {"X-EBAY-C-MARKETPLACE-ID": settings.EBAY_MARKETPLACE_ID}
    try:
        item = client.request(
            "GET", BROWSE_ITEM, access_token=get_app_token(), headers=headers,
            params={"legacy_item_id": listing_id},
        )
        return Decimal((item.get("price") or {})["value"])
    except (APIException, KeyError, InvalidOperation):
        return None
