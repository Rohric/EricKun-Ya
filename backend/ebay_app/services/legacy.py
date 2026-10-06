"""Listings created outside the Inventory API ("legacy"): read them, number them, convert them."""

from rest_framework.exceptions import APIException

from ebay_app.client import as_list
from ebay_app.exceptions import EbayApiError
from ebay_app.services.oauth import call, trading_call
from ebay_app.utils import to_decimal

MIGRATE_PATH = "/sell/inventory/v1/bulk_migrate_listing"
PAGE_SIZE = 200  # eBay's maximum per page
FIXED_PRICE = ("FixedPriceItem", "StoresFixedPrice")  # everything else is an auction
NOT_MIGRATED = "eBay hat das Inserat nicht umgewandelt."


def active_listings():
    """Return a snapshot of every listing that is online in the seller's account right now."""
    snapshots, page, pages = [], 1, 1
    while page <= pages:
        active = _active_page(page)
        snapshots += [_snapshot(item) for item in as_list((active.get("ItemArray") or {}).get("Item"))]
        pages = int((active.get("PaginationResult") or {}).get("TotalNumberOfPages") or 1)
        page += 1
    return snapshots


def _active_page(page):
    """Load one page of the seller's active listings (GetMyeBaySelling)."""
    pagination = {"EntriesPerPage": PAGE_SIZE, "PageNumber": page}
    body = {"ActiveList": {"Include": "true", "Pagination": pagination}}
    return trading_call("GetMyeBaySelling", body).get("ActiveList") or {}


def _snapshot(item):
    """Map a Trading API item to the fields a listing row stores."""
    price = (item.get("SellingStatus") or {}).get("CurrentPrice") or item.get("BuyItNowPrice")
    return {
        "listing_id": item.get("ItemID", ""),
        "sku": item.get("SKU", ""),
        "title": item.get("Title", ""),
        "price": to_decimal(price),
        "synced_quantity": int(item.get("QuantityAvailable") or item.get("Quantity") or 0),
        "image_url": (item.get("PictureDetails") or {}).get("GalleryURL", ""),
        "supported": item.get("ListingType") in FIXED_PRICE and not item.get("Variations"),
    }


def policies(listing_id):
    """Return the business policy ids a listing uses (GetItem); a converted offer does not tell them."""
    item = trading_call("GetItem", {"ItemID": listing_id}).get("Item") or {}
    profiles = item.get("SellerProfiles") or {}
    return {
        "fulfillmentPolicyId": (profiles.get("SellerShippingProfile") or {}).get("ShippingProfileID", ""),
        "returnPolicyId": (profiles.get("SellerReturnProfile") or {}).get("ReturnProfileID", ""),
        "paymentPolicyId": (profiles.get("SellerPaymentProfile") or {}).get("PaymentProfileID", ""),
    }


def set_sku(listing_id, sku):
    """Write our article number onto a legacy listing (ReviseFixedPriceItem)."""
    trading_call("ReviseFixedPriceItem", {"Item": {"ItemID": listing_id, "SKU": sku}})


def restore_sku(listing_id, sku):
    """Put a legacy listing's previous number back after a refused conversion (best effort)."""
    item = {"ItemID": listing_id}
    body = {"Item": {**item, "SKU": sku}} if sku else {"Item": item, "DeletedField": "Item.SKU"}
    try:
        trading_call("ReviseFixedPriceItem", body)
    except APIException:
        pass  # the next pull shows the number eBay really holds


def migrate(listing_id):
    """Convert a legacy listing into inventory item and offer; return (article number, offer id)."""
    body = {"requests": [{"listingId": listing_id}]}
    response = (call("POST", MIGRATE_PATH, json=body).get("responses") or [{}])[0]
    items = response.get("inventoryItems") or []
    if not items:
        raise EbayApiError(_refusal(response))
    return items[0]["sku"], items[0]["offerId"]


def _refusal(response):
    """Return eBay's reasons for not converting a listing."""
    errors = response.get("errors") or []
    texts = [error.get("longMessage") or error.get("message", "") for error in errors]
    return " · ".join(filter(None, texts)) or NOT_MIGRATED
