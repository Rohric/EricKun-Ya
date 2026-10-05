"""Put products online on eBay: inventory item, offer, publish, sync and withdraw."""

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from ebay_app import client
from ebay_app.exceptions import EbayApiError
from ebay_app.models import EbayAccount, EbayListing, EbayLocation
from ebay_app.services import images, taxonomy
from ebay_app.services.conditions import condition_note, ebay_condition
from ebay_app.services.oauth import call
from ebay_app.services.overview import connection_status
from products_app.models import Product

logger = logging.getLogger(__name__)

INVENTORY = "/sell/inventory/v1"
LANGUAGE = {"Content-Language": client.LOCALE}
CURRENCY = "EUR"
TITLE_MAX = 80  # eBay's limit for listing titles
ENDING_STATES = (Product.Status.SOLD, Product.Status.ARCHIVED)
ONLINE = EbayListing.Status.ONLINE
NOT_READY = "eBay ist noch nicht fertig eingerichtet. Bitte zuerst die Checkliste im eBay-Reiter abschließen."
NOT_SELLABLE = "Nur verfügbare Artikel mit Bestand können inseriert werden."
TITLE_TOO_LONG = f"Der Titel darf bei eBay höchstens {TITLE_MAX} Zeichen haben."
NO_LISTING = "Dieser Artikel wurde noch nicht inseriert."
MISSING_ASPECTS = "Pflicht-Merkmale fehlen: {names}"


# --- Overview ---

def listing_products():
    """Return all products with their eBay listing and images preloaded."""
    return Product.objects.select_related("ebay_listing").prefetch_related("images").order_by("-created_at")


def active_listing_products():
    """Return the products that are not sold or archived, i.e. the ones that can be listed."""
    return listing_products().exclude(status__in=ENDING_STATES)


def listing_url(listing):
    """Return the public eBay page of an online listing, or an empty string."""
    if not listing.listing_id:
        return ""
    return f"{client.environment()['web']}/itm/{listing.listing_id}"


# --- Actions ---

def publish(product, category, aspects):
    """Store the chosen category and aspects, then put the product online."""
    _require_sellable(product)
    _store_aspects(product, category["id"], aspects)
    defaults = {"category_id": category["id"], "category_name": category["name"]}
    listing, _ = EbayListing.objects.update_or_create(product=product, defaults=defaults)
    return _push(listing)


def sync(product):
    """Push the product's current data to eBay and make sure its listing is online."""
    listing = _listing_of(product)
    _require_sellable(product)
    return _push(listing)


def withdraw(product):
    """End the product's eBay listing; the offer stays and can be published again."""
    listing = _listing_of(product)
    if listing.status == ONLINE:
        call("POST", f"{INVENTORY}/offer/{listing.offer_id}/withdraw")
    listing.listing_id = ""
    return _mark(listing, EbayListing.Status.ENDED)


def sync_all():
    """Sync every online listing with local changes; failures are stored per listing."""
    result = {"synced": 0, "failed": 0}
    for listing in EbayListing.objects.filter(status=ONLINE).select_related("product"):
        if listing.has_unsynced_changes or listing.sync_error:
            result["synced" if _try(sync, listing) else "failed"] += 1
    return result


def end_if_unsellable(product):
    """End the online listing of a sold-out or archived product; errors are stored, not raised."""
    listing = EbayListing.objects.filter(product=product, status=ONLINE).first()
    if listing and (product.quantity == 0 or product.status in ENDING_STATES):
        _try(withdraw, listing)


def remove_item(sku):
    """Delete an inventory item on eBay, which also ends its listing and removes its offers."""
    try:
        call("DELETE", f"{INVENTORY}/inventory_item/{sku}")
    except APIException as exc:
        logger.warning("Could not remove %s from eBay: %s", sku, exc.detail)


# --- Checks ---

def _require_sellable(product):
    """Raise unless eBay is fully set up and the product can be offered."""
    if not connection_status()["ready"]:
        raise ValidationError(NOT_READY)
    if product.status != Product.Status.AVAILABLE or product.quantity < 1:
        raise ValidationError(NOT_SELLABLE)
    if len(product.title) > TITLE_MAX:
        raise ValidationError(TITLE_TOO_LONG)


def _listing_of(product):
    """Return the product's listing or raise if it was never listed."""
    listing = EbayListing.objects.filter(product=product).first()
    if listing is None:
        raise ValidationError(NO_LISTING)
    listing.product = product  # reuse the loaded instance instead of querying it again
    return listing


def _store_aspects(product, category_id, aspects):
    """Merge the entered aspects into the product after checking the required ones."""
    merged = {name: values for name, values in {**product.aspects, **aspects}.items() if values}
    required = [aspect["name"] for aspect in taxonomy.category_aspects(category_id) if aspect["required"]]
    missing = [name for name in required if name not in merged]
    if missing:
        raise ValidationError(MISSING_ASPECTS.format(names=", ".join(missing)))
    product.aspects = merged
    product.save(update_fields=["aspects", "updated_at"])


# --- Transfer ---

def _push(listing):
    """Transfer item and offer, publish the offer if needed and record the synced state."""
    sku = listing.product.sku
    call("PUT", f"{INVENTORY}/inventory_item/{sku}", headers=LANGUAGE, json=_item_payload(listing))
    _save_offer(listing)
    if listing.status != ONLINE:
        listing.listing_id = call("POST", f"{INVENTORY}/offer/{listing.offer_id}/publish")["listingId"]
    return _mark(listing, ONLINE)


def _save_offer(listing):
    """Create the offer or update the existing one, so a SKU never gets a second offer."""
    if not listing.offer_id:
        _adopt_remote_offer(listing)
    payload = _offer_payload(listing)
    if listing.offer_id:
        call("PUT", f"{INVENTORY}/offer/{listing.offer_id}", headers=LANGUAGE, json=payload)
    else:
        listing.offer_id = call("POST", f"{INVENTORY}/offer", headers=LANGUAGE, json=payload)["offerId"]
    listing.save(update_fields=["offer_id", "listing_id", "status"])


def _adopt_remote_offer(listing):
    """Take over an offer eBay already has for the SKU (e.g. after a database reset)."""
    offer = _remote_offer(listing.product.sku)
    if offer is None:
        return
    listing.offer_id = offer["offerId"]
    if offer.get("status") == "PUBLISHED":
        listing.listing_id = (offer.get("listing") or {}).get("listingId", "")
        listing.status = ONLINE


def _remote_offer(sku):
    """Return eBay's offer for a SKU, or None (eBay answers 404 if there is none)."""
    params = {"sku": sku, "marketplace_id": settings.EBAY_MARKETPLACE_ID}
    try:
        offers = call("GET", f"{INVENTORY}/offer", params=params).get("offers", [])
    except EbayApiError as exc:
        if exc.http_status == 404:
            return None
        raise
    return offers[0] if offers else None


def _mark(listing, status):
    """Store the new status together with what eBay now knows about the product."""
    listing.status = status
    listing.synced_quantity = listing.product.quantity
    listing.last_synced = timezone.now()
    listing.sync_error = ""
    listing.save()
    return listing


def _try(action, listing):
    """Run a listing action; store an eBay or validation error on the listing instead of raising."""
    try:
        action(listing.product)
    except APIException as exc:
        EbayListing.objects.filter(pk=listing.pk).update(sync_error=_error_text(exc))
        return False
    return True


def _error_text(exc):
    """Return an API exception's detail as one plain string."""
    detail = exc.detail
    return " ".join(str(part) for part in detail) if isinstance(detail, list) else str(detail)


# --- Payloads ---

def _item_payload(listing):
    """Build the createOrReplaceInventoryItem body for the listing's product."""
    product = listing.product
    condition = ebay_condition(product, taxonomy.allowed_condition_ids(listing.category_id))
    payload = {
        "availability": {"shipToLocationAvailability": {"quantity": product.quantity}},
        "condition": condition,
        "product": _product_payload(product),
    }
    note = condition_note(product, condition)
    if note:
        payload["conditionDescription"] = note
    return payload


def _product_payload(product):
    """Build the descriptive part of an inventory item (eBay requires a description)."""
    return {
        "title": product.title,
        "description": product.description or product.title,
        "aspects": {name: _as_list(values) for name, values in product.aspects.items()},
        "imageUrls": images.image_urls(product),
    }


def _as_list(values):
    """Return aspect values as the list of strings eBay expects."""
    return [str(value) for value in values] if isinstance(values, list) else [str(values)]


def _offer_payload(listing):
    """Build the offer body: price, quantity, category, location and policies."""
    product = listing.product
    return {
        "sku": product.sku,
        "marketplaceId": settings.EBAY_MARKETPLACE_ID,
        "format": "FIXED_PRICE",
        "availableQuantity": product.quantity,
        "categoryId": listing.category_id,
        "merchantLocationKey": EbayLocation.objects.get(warehouse__is_default=True).merchant_location_key,
        "pricingSummary": {"price": {"value": f"{product.sale_price:.2f}", "currency": CURRENCY}},
        "listingPolicies": _policy_ids(EbayAccount.load()),
    }


def _policy_ids(account):
    """Return the three business policy ids in the shape an offer expects."""
    return {
        "fulfillmentPolicyId": account.fulfillment_policy_id,
        "paymentPolicyId": account.payment_policy_id,
        "returnPolicyId": account.return_policy_id,
    }
