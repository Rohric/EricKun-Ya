"""Assign listings found on eBay to articles: link, create an article, ignore or unlink."""

from datetime import timedelta
from difflib import SequenceMatcher
from io import BytesIO

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image
from rest_framework.exceptions import APIException, ValidationError

from ebay_app import client
from ebay_app.models import EbayAccount, EbayImage, EbayListing
from ebay_app.services import legacy, shipping_profiles, snapshots
from ebay_app.services.conditions import product_condition
from ebay_app.services.images import MAX_IMAGES
from ebay_app.services.listings import listing_of, record_error
from products_app.models import Product, ProductImage

MIN_SIMILARITY = 0.6  # share of matching characters from which a title counts as "the same article"
TRUTHY = ("1", "true")
EXTENSIONS = {"JPEG": "jpg"}  # file endings that differ from Pillow's format name
HOSTED_FOR = timedelta(days=30)  # how long a picture address taken over from eBay is trusted
ONLINE = EbayListing.Status.ONLINE
ALREADY_LINKED = "Dieses Inserat ist bereits einem Artikel zugeordnet."
NOT_SUPPORTED = "Auktionen und Inserate mit Varianten werden nicht unterstützt."
PRODUCT_TAKEN = "Dieser Artikel hat bereits ein laufendes eBay-Inserat."
LEGACY_NOTE = "Altes Inserat: Beim Zuordnen bekommt es unsere Artikelnummer und wird umgewandelt."


# --- Overview ---

def unassigned(ignored=""):
    """Return the listings that wait for an article, or the ignored ones for ignored=1."""
    rows = EbayListing.objects.filter(product=None, ignored=str(ignored).lower() in TRUTHY)
    return rows.order_by("title", "pk")


def free_products():
    """Return the articles a listing can be linked to: not archived and not online on eBay."""
    online = EbayListing.objects.filter(status=ONLINE, product__isnull=False)
    return Product.objects.exclude(status=Product.Status.ARCHIVED).exclude(pk__in=online.values("product_id"))


def suggest(listing, products):
    """Return the free article that fits best (same number, else a similar title), or None."""
    same_number = [product for product in products if listing.sku and product.sku == listing.sku]
    if same_number:
        return same_number[0]
    scored = [(_similarity(listing.title, product.title), product) for product in products]
    score, product = max(scored, key=lambda pair: pair[0], default=(0, None))
    return product if score >= MIN_SIMILARITY else None


def _similarity(first, second):
    """Return how alike two titles are, from 0 (nothing in common) to 1 (identical)."""
    return SequenceMatcher(None, first.lower(), second.lower()).ratio()


def notes(listing):
    """Return the hints shown with an unassigned listing, eBay's last refusal included."""
    hints = []
    if not listing.supported:
        hints.append(NOT_SUPPORTED)
    elif listing.needs_migration:
        hints.append(LEGACY_NOTE)
    return [*hints, listing.sync_error] if listing.sync_error else hints


# --- Actions ---

def link(listing, product):
    """Link an unassigned listing to an article; from then on the article is the truth."""
    _require_linkable(listing, product)
    try:
        _convert_if_legacy(listing, product.sku)
        details = snapshots.read_details(listing.sku)
        _adopt_policies(listing, _policies_of(listing, details))
    except APIException as exc:
        record_error(listing, exc)  # the row keeps showing why eBay refused
        raise
    snapshots.apply_snapshot(listing, details["snapshot"])
    _fill_gaps(product, details)
    return _attach(listing, product)


def link_exact_matches():
    """Link every open listing to the free article with exactly the same number; return how many."""
    linked = 0
    rows = unassigned().filter(needs_migration=False, supported=True).exclude(sku="")
    for listing in rows:
        product = free_products().filter(sku=listing.sku).first()
        if product:
            _attach(listing, product)
            linked += 1
    return linked


def create_product(listing):
    """Create an article with a new internal number from an unassigned listing and link both."""
    _require_open(listing)
    product = _new_product(listing)
    try:
        _convert_if_legacy(listing, product.sku)
        _take_over(listing, product)
    except APIException as exc:
        product.delete()  # not linked yet, so nothing is removed on eBay
        record_error(listing, exc)
        raise
    _attach(listing, product)
    return product


def create_all():
    """Create an article for every open, supported listing; return how many worked and failed."""
    result = {"created": 0, "failed": 0}
    for listing in unassigned().filter(supported=True):
        try:
            create_product(listing)
            result["created"] += 1
        except APIException:
            result["failed"] += 1  # eBay's reason is stored on the listing
    return result


def ignore(listing, ignored=True):
    """Hide an unassigned listing from the assignment view, or show it again."""
    if listing.product_id is not None:
        raise ValidationError(ALREADY_LINKED)
    listing.ignored = ignored
    listing.save(update_fields=["ignored"])
    return listing


def unlink(product):
    """Detach the article's listing: an online one waits for assignment again, any other is dropped."""
    listing = listing_of(product)
    if listing.status != ONLINE:
        listing.delete()
        return None
    listing.product = None
    listing.save(update_fields=["product"])
    return listing


# --- Checks and bookkeeping ---

def _require_open(listing):
    """Raise unless the listing is unassigned and of a kind we can manage."""
    if listing.product_id is not None:
        raise ValidationError(ALREADY_LINKED)
    if not listing.supported:
        raise ValidationError(NOT_SUPPORTED)


def _require_linkable(listing, product):
    """Raise unless the listing is open and the article has no listing that is online."""
    _require_open(listing)
    if EbayListing.objects.filter(product=product, status=ONLINE).exists():
        raise ValidationError(PRODUCT_TAKEN)


def _attach(listing, product):
    """Store the link; an older row of the article that is no longer online makes way."""
    EbayListing.objects.filter(product=product).exclude(pk=listing.pk).delete()
    listing.product, listing.ignored, listing.sync_error = product, False, ""
    listing.last_synced = timezone.now()  # from now on only later changes count as "changed"
    listing.save()
    return listing


def _convert_if_legacy(listing, sku):
    """Give a legacy listing our number and convert it, so the Inventory API can manage it."""
    if not listing.needs_migration:
        return
    legacy.set_sku(listing.listing_id, sku)
    try:
        listing.sku, listing.offer_id = legacy.migrate(listing.listing_id)
    except APIException:
        legacy.restore_sku(listing.listing_id, listing.sku)  # eBay refused: the old number comes back
        raise
    listing.needs_migration = False
    listing.save(update_fields=["sku", "offer_id", "needs_migration"])


def _policies_of(listing, details):
    """Return the listing's policy ids; a converted listing only reveals them through the Trading API."""
    policies = details["policies"]
    if policies.get("fulfillmentPolicyId") or not listing.listing_id:
        return policies
    return legacy.policies(listing.listing_id)


def _adopt_policies(listing, policies):
    """Keep the listing's own shipping policy as its profile; adopt return/payment if we have none."""
    listing.shipping_profile = shipping_profiles.adopt(policies.get("fulfillmentPolicyId", ""))
    account = EbayAccount.load()
    account.return_policy_id = account.return_policy_id or policies.get("returnPolicyId", "")
    account.payment_policy_id = account.payment_policy_id or policies.get("paymentPolicyId", "")
    account.save(update_fields=["return_policy_id", "payment_policy_id"])


# --- Article data ---

def _new_product(listing):
    """Create the article from what the row knows; the purchase price is unknown and starts at 0."""
    return Product.objects.create(
        title=listing.title or listing.sku or listing.listing_id,
        purchase_price=0,
        sale_price=listing.price or 0,
        quantity=listing.synced_quantity,
    )


def _take_over(listing, product):
    """Copy eBay's data into the new article: details, policies and pictures."""
    details = snapshots.read_details(listing.sku)
    _adopt_policies(listing, _policies_of(listing, details))
    snapshots.apply_snapshot(listing, details["snapshot"])
    product.title, product.sale_price = listing.title or product.title, listing.price or 0
    product.quantity, product.aspects = listing.synced_quantity, details["aspects"]
    product.description = details["description"]
    product.condition = product_condition(details["condition"], details["condition_note"])
    product.save()
    _copy_images(product, details["image_urls"])


def _fill_gaps(product, details):
    """Add what a linked article lacks from its listing (aspects, description); its own data wins."""
    product.aspects = {**details["aspects"], **product.aspects}
    product.description = product.description or details["description"]
    product.save(update_fields=["aspects", "description", "updated_at"])


def _copy_images(product, urls):
    """Download the listing's pictures as product images and remember their eBay addresses."""
    for position, url in enumerate(urls[:MAX_IMAGES]):
        picture = _picture(url)
        if picture is None:
            continue  # a picture that cannot be loaded must not stop the takeover
        content, extension = picture
        image = ProductImage(product=product, position=position)
        image.image.save(f"{position + 1}.{extension}", ContentFile(content))
        expires = timezone.now() + HOSTED_FOR  # afterwards a sync uploads our own copy again
        EbayImage.objects.create(image=image, eps_url=url, source_name=image.image.name, expires_at=expires)


def _picture(url):
    """Return (bytes, file ending) of a listing picture, or None if it is no loadable image."""
    try:
        content = client.download(url)
        kind = Image.open(BytesIO(content)).format or ""
    except (APIException, OSError):
        return None
    return content, EXTENSIONS.get(kind, kind.lower())
