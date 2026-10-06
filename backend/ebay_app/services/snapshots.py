"""Read what eBay holds about a listing and copy it onto our listing row."""

from ebay_app.models import EbayListing
from ebay_app.services.listings import item_path, remote_offer
from ebay_app.services.oauth import call
from ebay_app.utils import to_decimal

PUBLISHED = "PUBLISHED"  # offer status of a listing that is online


def inventory_snapshot(item, offer):
    """Map an inventory item and its offer (or None) to the fields a listing row stores."""
    return {"sku": item["sku"], **_item_fields(item), **_offer_fields(offer or {})}


def _item_fields(item):
    """Return title, picture, stock and support flag of an inventory item."""
    product = item.get("product") or {}
    stock = (item.get("availability") or {}).get("shipToLocationAvailability") or {}
    return {
        "title": product.get("title", ""),
        "image_url": (product.get("imageUrls") or [""])[0],
        "synced_quantity": int(stock.get("quantity") or 0),
        "supported": not item.get("groupIds"),  # items of a group are variations of one listing
    }


def _offer_fields(offer):
    """Return ids, category, price and options of an offer; without offer only "not online"."""
    if not offer:
        return {"online": False}
    online = offer.get("status") == PUBLISHED
    policies = offer.get("listingPolicies") or {}
    return {
        "offer_id": offer.get("offerId", ""),
        "listing_id": (offer.get("listing") or {}).get("listingId", "") if online else "",
        "category_id": offer.get("categoryId", ""),
        "price": to_decimal(((offer.get("pricingSummary") or {}).get("price") or {}).get("value")),
        "best_offer": bool((policies.get("bestOfferTerms") or {}).get("bestOfferEnabled")),
        "online": online,
    }


def apply_snapshot(listing, snapshot):
    """Copy a snapshot onto the row and save it; a listing that left eBay counts as ended."""
    online = snapshot.pop("online")
    for field, value in snapshot.items():
        setattr(listing, field, value)
    if online:
        listing.status = EbayListing.Status.ONLINE
    elif listing.status == EbayListing.Status.ONLINE:
        listing.status, listing.listing_id = EbayListing.Status.ENDED, ""
    listing.save()
    return listing


def read_details(sku):
    """Read everything eBay holds under an article number: the row's fields plus the article data."""
    item, offer = call("GET", item_path(sku)), remote_offer(sku) or {}
    product = item.get("product") or {}
    return {
        "snapshot": inventory_snapshot({**item, "sku": sku}, offer),
        "description": offer.get("listingDescription") or product.get("description", ""),
        "aspects": product.get("aspects") or {},
        "condition": item.get("condition", ""),
        "condition_note": item.get("conditionDescription", ""),
        "image_urls": product.get("imageUrls") or [],
        "policies": offer.get("listingPolicies") or {},
    }
