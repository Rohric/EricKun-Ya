"""Put products online on eBay: inventory item, offer, publish, sync, withdraw and fee preview."""

import logging
from decimal import Decimal

from django.conf import settings
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from ebay_app import client
from ebay_app.exceptions import EbayApiError
from ebay_app.models import EbayAccount, EbayCategoryMapping, EbayListing, EbayLocation, EbayShippingProfile
from ebay_app.services import facts, images, taxonomy
from ebay_app.services.conditions import condition_hint, condition_note, ebay_condition
from ebay_app.services.oauth import call
from ebay_app.services.overview import connection_status
from orders_app.models import Order
from products_app.models import Product

logger = logging.getLogger(__name__)

INVENTORY = "/sell/inventory/v1"
LANGUAGE = {"Content-Language": client.LOCALE}
CURRENCY = "EUR"
TITLE_MAX = 80  # eBay's limit for listing titles
ENDING_STATES = (Product.Status.SOLD, Product.Status.ARCHIVED)
ONLINE = EbayListing.Status.ONLINE
LISTED_STATES = (EbayListing.Status.ONLINE, EbayListing.Status.ENDED)
NOT_READY = "eBay ist noch nicht fertig eingerichtet. Bitte zuerst die Checkliste im eBay-Reiter abschließen."
NOT_SELLABLE = "Nur verfügbare Artikel mit Bestand können inseriert werden."
TITLE_TOO_LONG = f"Der Titel darf bei eBay höchstens {TITLE_MAX} Zeichen haben."
NO_LISTING = "Dieser Artikel wurde noch nicht inseriert."
MISSING_ASPECTS = "Pflicht-Merkmale fehlen: {names}"
BAD_SCOPE = "Unbekannter Bereich. Erlaubt: all, listed, unlisted."
NO_PREVIEW_ONLINE = "Für ein laufendes Inserat gibt es keine Gebühren-Vorschau."


# --- Overview ---

def listing_products():
    """Return all products with listing, profile, remembered category, images and units sold on eBay."""
    sold_on_ebay = Q(order_items__order__ebay_order_id__isnull=False) & ~Q(
        order_items__order__fulfillment_status=Order.Fulfillment.CANCELLED
    )
    return (
        Product.objects.select_related("ebay_listing__shipping_profile", "category__parent", "category__ebay_mapping")
        .prefetch_related("images")
        .annotate(sold_units=Coalesce(Sum("order_items__quantity", filter=sold_on_ebay), 0))
        .order_by("-created_at")
    )


def active_listing_products():
    """Return the products that are not sold or archived, i.e. the ones that can be listed."""
    return listing_products().exclude(status__in=ENDING_STATES)


def products_in_scope(scope):
    """Return the products of one eBay tab: listed, unlisted or all sellable ones."""
    if scope == "listed":
        return listing_products().filter(ebay_listing__status__in=LISTED_STATES)
    if scope == "unlisted":
        not_online = Q(ebay_listing__isnull=True) | Q(ebay_listing__status=EbayListing.Status.DRAFT)
        return active_listing_products().filter(not_online)
    if scope in ("", "all"):
        return active_listing_products()
    raise ValidationError(BAD_SCOPE)


def channel_states():
    """Return {product id: [channel entries]} so the product page can show where an article is listed."""
    listings = EbayListing.objects.select_related("product")
    return {str(listing.product_id): [_channel_entry(listing)] for listing in listings}


def _channel_entry(listing):
    """Describe a listing as one sales channel of its product."""
    return {"channel": "ebay", "label": "eBay", "state": listing.state, "url": listing_url(listing)}


def listing_url(listing):
    """Return the public eBay page of an online listing, or an empty string."""
    if not listing.listing_id:
        return ""
    return f"{client.environment()['web']}/itm/{listing.listing_id}"


def requirements(category_id, product_id=""):
    """Return a category's aspects and conditions, plus a condition hint for one product."""
    data = taxonomy.category_requirements(category_id)
    product = Product.objects.filter(pk=product_id).first() if str(product_id).isdigit() else None
    data["condition_hint"] = condition_hint(product, set(data["condition_ids"])) if product else ""
    return data


# --- Actions ---

def publish(product, category, aspects, **options):
    """Store the listing choices, put the product online and remember the category."""
    listing = _prepare(product, category, aspects, options)
    _push_or_record(listing)
    _remember_category(product, category)
    return listing


def preview(product, category, aspects, **options):
    """Transfer item and offer without publishing and return eBay's expected listing fees."""
    if EbayListing.objects.filter(product=product, status=ONLINE).exists():
        raise ValidationError(NO_PREVIEW_ONLINE)
    listing = _prepare(product, category, aspects, options)
    _transfer(listing)
    return _fees(listing)


def sync(product):
    """Push the product's current data to eBay and make sure its listing is online."""
    listing = _listing_of(product)
    _require_sellable(product)
    return _push_or_record(listing)


def withdraw(product):
    """End the product's eBay listing; the offer stays and can be published again."""
    listing = _listing_of(product)
    if listing.offer_id and _published_listing_id(listing):
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


# --- Checks and bookkeeping ---

def _prepare(product, category, aspects, options):
    """Check the product, store aspects and listing choices, and return the listing."""
    _require_sellable(product)
    _store_aspects(product, category["id"], aspects)
    defaults = {
        "category_id": category["id"],
        "category_name": category["name"],
        "shipping_profile": options.get("shipping_profile"),
        "best_offer": bool(options.get("best_offer")),
    }
    listing, _ = EbayListing.objects.update_or_create(product=product, defaults=defaults)
    listing.product = product  # reuse the loaded instance instead of querying it again
    return listing


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
    listing = EbayListing.objects.select_related("shipping_profile").filter(product=product).first()
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


def _remember_category(product, category):
    """Remember the eBay category for the product's internal category (pre-selected next time)."""
    if not product.category_id:
        return
    defaults = {"ebay_category_id": category["id"], "ebay_category_name": category["name"]}
    EbayCategoryMapping.objects.update_or_create(category_id=product.category_id, defaults=defaults)


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
        _record_error(listing, exc)
        return False
    return True


def _push_or_record(listing):
    """Transfer the listing; on failure keep eBay's reason on the listing, then re-raise it."""
    try:
        return _push(listing)
    except APIException as exc:
        _record_error(listing, exc)  # the row keeps showing why it is not online
        raise


def _record_error(listing, exc):
    """Store an API exception's text as the listing's sync error."""
    EbayListing.objects.filter(pk=listing.pk).update(sync_error=_error_text(exc))


def _error_text(exc):
    """Return an API exception's detail as one plain string."""
    detail = exc.detail
    return " ".join(str(part) for part in detail) if isinstance(detail, list) else str(detail)


# --- Transfer ---

def _push(listing):
    """Transfer item and offer, publish the offer unless eBay already shows it, record the state."""
    _transfer(listing)
    listing.listing_id = _published_listing_id(listing) or _publish_offer(listing)
    _mark(listing, ONLINE)
    facts.refresh_quietly(listing)
    return listing


def _transfer(listing):
    """Create or replace the inventory item and its offer on eBay (nothing is published here)."""
    sku = listing.product.sku
    call("PUT", f"{INVENTORY}/inventory_item/{sku}", headers=LANGUAGE, json=_item_payload(listing))
    _save_offer(listing)


def _save_offer(listing):
    """Create the offer or update the existing one, so a SKU never gets a second offer."""
    if not listing.offer_id:
        listing.offer_id = _remote_offer_id(listing.product.sku)
    payload = _offer_payload(listing)
    if listing.offer_id:
        call("PUT", f"{INVENTORY}/offer/{listing.offer_id}", headers=LANGUAGE, json=payload)
    else:
        listing.offer_id = call("POST", f"{INVENTORY}/offer", headers=LANGUAGE, json=payload)["offerId"]
    listing.save(update_fields=["offer_id"])


def _remote_offer_id(sku):
    """Return the id of an offer eBay already has for the SKU, or "" (eBay answers 404 if none)."""
    params = {"sku": sku, "marketplace_id": settings.EBAY_MARKETPLACE_ID}
    try:
        offers = call("GET", f"{INVENTORY}/offer", params=params).get("offers", [])
    except EbayApiError as exc:
        if exc.http_status == 404:
            return ""
        raise
    return offers[0]["offerId"] if offers else ""


def _published_listing_id(listing):
    """Return the listing id if eBay shows the offer as published, else "" (eBay's state decides)."""
    offer = call("GET", f"{INVENTORY}/offer/{listing.offer_id}")
    if offer.get("status") != "PUBLISHED":
        return ""
    return (offer.get("listing") or {}).get("listingId", "")


def _publish_offer(listing):
    """Publish the offer and return the id of the new eBay listing."""
    return call("POST", f"{INVENTORY}/offer/{listing.offer_id}/publish")["listingId"]


def _fees(listing):
    """Ask eBay for the fees of the unpublished offer and return them with their sum."""
    body = {"offers": [{"offerId": listing.offer_id}]}
    summaries = call("POST", f"{INVENTORY}/offer/get_listing_fees", json=body).get("feeSummaries") or [{}]
    fees = [_fee(raw) for raw in summaries[0].get("fees", [])]
    charged = [fee for fee in fees if Decimal(fee["amount"]) > 0]  # eBay lists every fee type, most are 0
    total = sum((Decimal(fee["amount"]) for fee in charged), Decimal("0"))
    return {"fees": charged, "total": f"{total:.2f}", "currency": CURRENCY}


def _fee(raw):
    """Map one eBay fee entry to {type, amount}."""
    return {"type": raw.get("feeType", ""), "amount": (raw.get("amount") or {}).get("value", "0")}


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
        "pricingSummary": {"price": {"value": f"{Decimal(product.sale_price):.2f}", "currency": CURRENCY}},
        "listingPolicies": _listing_policies(listing),
    }


def _listing_policies(listing):
    """Return the policy ids of the listing's shipping profile, return and payment, plus best offer."""
    account = EbayAccount.load()
    profile = listing.shipping_profile or EbayShippingProfile.default()
    policies = {
        "fulfillmentPolicyId": profile.policy_id,
        "paymentPolicyId": account.payment_policy_id,
        "returnPolicyId": account.return_policy_id,
    }
    if listing.best_offer:  # an offer is replaced as a whole, so leaving it out switches it off
        policies["bestOfferTerms"] = {"bestOfferEnabled": True}
    return policies
