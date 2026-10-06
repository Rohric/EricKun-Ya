"""Bring eBay sales into orders_app and report shipments back to eBay."""

from datetime import timedelta, timezone as dt_timezone
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from ebay_app.models import EbayAccount, EbayListing
from ebay_app.services.oauth import call
from orders_app.models import Cancellation, Order, OrderItem
from orders_app.services import cancel_order, sync_stock
from products_app.models import Product

ORDERS = "/sell/fulfillment/v1/order"
PAGE_SIZE = 50
FIRST_IMPORT_DAYS = 90
OVERLAP = timedelta(minutes=5)  # re-read a little so no late change is missed
PAID_STATES = ("PAID", "PARTIALLY_REFUNDED")
OPEN_PAYMENT_STATES = ("PENDING",)  # eBay reserves the item, so the stock is booked right away
SIMULATED_PREFIX = "SIM-"  # order ids created by the sandbox sale simulation
CARRIERS = [
    {"code": "DHL", "name": "DHL"},
    {"code": "Hermes", "name": "Hermes"},
    {"code": "DPD", "name": "DPD"},
    {"code": "GLS", "name": "GLS"},
    {"code": "UPS", "name": "UPS"},
    {"code": "DeutschePost", "name": "Deutsche Post"},
]
CANCELLED_ON_EBAY = "Bei eBay storniert."
NOT_FROM_EBAY = "Diese Bestellung stammt nicht von eBay."
IS_CANCELLED = "Eine stornierte Bestellung kann nicht verschickt werden."
NOT_PAID = "Die Zahlung ist noch offen. Bitte erst nach Zahlungseingang verschicken."


def _is_simulated(order):
    """Return True for orders created by the sandbox sale simulation (eBay does not know them)."""
    return settings.EBAY_ENV == "sandbox" and (order.ebay_order_id or "").startswith(SIMULATED_PREFIX)


# --- Import ---

def import_orders():
    """Fetch new and changed eBay orders; return what was created, paid and cancelled."""
    account = EbayAccount.load()
    started = timezone.now()
    result = import_payloads(_changed_orders(account.orders_synced_at))
    account.orders_synced_at = started
    account.save(update_fields=["orders_synced_at"])
    return result


def import_payloads(payloads):
    """Process eBay order payloads (real or simulated); return what was created, paid and cancelled."""
    result = {"created": 0, "paid": 0, "cancelled": 0, "unknown_skus": []}
    for payload in payloads:
        _import_one(payload, result)
    return result


def _changed_orders(since):
    """Yield every eBay order modified since the last import (first run: the last 90 days)."""
    start = since - OVERLAP if since else timezone.now() - timedelta(days=FIRST_IMPORT_DAYS)
    params = {"filter": f"lastmodifieddate:[{_ebay_time(start)}..]", "limit": PAGE_SIZE, "offset": 0}
    while True:
        page = call("GET", ORDERS, params=params)
        yield from page.get("orders", [])
        params["offset"] += PAGE_SIZE
        if params["offset"] >= page.get("total", 0):
            return


def _ebay_time(moment):
    """Format a datetime the way eBay's order filters expect it (UTC, milliseconds)."""
    return moment.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


@transaction.atomic
def _import_one(payload, result):
    """Create a new order, cancel a known one or mark it paid – whatever eBay reports."""
    order = Order.objects.filter(ebay_order_id=payload["orderId"]).first()
    cancelled = (payload.get("cancelStatus") or {}).get("cancelState") == "CANCELED"
    if order is None:
        _create_if_wanted(payload, cancelled, result)
    elif cancelled:
        _cancel_known(order, result)
    else:
        _mark_paid(order, payload, result)


def _create_if_wanted(payload, cancelled, result):
    """Create the order unless eBay shows it as cancelled, failed or fully refunded."""
    payment = _payment_status(payload)
    if cancelled or payment is None:
        return
    _create_order(payload, payment, result)
    result["created"] += 1


def _payment_status(payload):
    """Translate eBay's payment status; None for states that are not worth an order."""
    status = payload.get("orderPaymentStatus")
    if status in PAID_STATES:
        return Order.Payment.PAID
    return Order.Payment.PENDING if status in OPEN_PAYMENT_STATES else None


def _cancel_known(order, result):
    """Cancel a local order that eBay now shows as cancelled, and restock its items."""
    if order.fulfillment_status == Order.Fulfillment.CANCELLED:
        return
    cancel_order(order, Cancellation.ItemAction.AVAILABLE, CANCELLED_ON_EBAY, Cancellation.Source.EBAY)
    result["cancelled"] += 1


def _mark_paid(order, payload, result):
    """Set a waiting order to paid once eBay reports the payment."""
    if order.payment_status == Order.Payment.PAID or _payment_status(payload) != Order.Payment.PAID:
        return
    order.payment_status = Order.Payment.PAID
    order.save(update_fields=["payment_status"])
    result["paid"] += 1


def _create_order(payload, payment, result):
    """Create the local order with buyer data and items, then book the stock."""
    order = Order.objects.create(
        ebay_order_id=payload["orderId"],
        sold_at=parse_datetime(payload["creationDate"]),
        payment_status=payment,
        ebay_username=(payload.get("buyer") or {}).get("username", ""),
        **_shipping_fields(payload),
    )
    for line in payload.get("lineItems", []):
        _create_item(order, line, result)
    sync_stock(order, sign=-1)


def _shipping_fields(payload):
    """Extract the buyer's name and delivery address from an eBay order."""
    instructions = payload.get("fulfillmentStartInstructions") or [{}]
    ship_to = (instructions[0].get("shippingStep") or {}).get("shipTo") or {}
    address = ship_to.get("contactAddress") or {}
    street = " ".join(filter(None, [address.get("addressLine1"), address.get("addressLine2")]))
    return {
        "buyer_name": ship_to.get("fullName", ""),
        "ship_street": street,
        "ship_zip": address.get("postalCode", ""),
        "ship_city": address.get("city", ""),
        "ship_country": address.get("countryCode", ""),
    }


def _create_item(order, line, result):
    """Create one line item; a sale that fits no article is kept without product and reported."""
    listing = _listing_for(line)
    product = listing.product if listing and listing.product_id else _product_by_number(line)
    quantity = int(line.get("quantity") or 1)
    if product is None:
        result["unknown_skus"].append(line.get("sku") or line.get("title", "?"))
    _mirror_sold_quantity(listing, quantity)
    OrderItem.objects.create(
        order=order, product=product, quantity=quantity,
        sold_price=_unit_price(line, quantity), ebay_line_item_id=line.get("lineItemId", ""),
    )


def _listing_for(line):
    """Find the listing of a sold line by the number eBay knows, else by the eBay item id."""
    sku, item_id = line.get("sku"), line.get("legacyItemId")
    listings = EbayListing.objects.select_related("product")
    found = listings.filter(sku=sku).first() if sku else None
    return found or (listings.filter(listing_id=item_id).first() if item_id else None)


def _product_by_number(line):
    """Return the product whose own article number equals the sold SKU, or None."""
    return Product.objects.filter(sku=line.get("sku") or "").first()


def _unit_price(line, quantity):
    """Return the price per unit; eBay reports the cost of the whole line."""
    total = Decimal((line.get("lineItemCost") or {}).get("value", "0"))
    return (total / quantity).quantize(Decimal("0.01"))


def _mirror_sold_quantity(listing, quantity):
    """Lower the listing's synced quantity, because eBay already reduced its own stock."""
    if listing is None:
        return
    listing.synced_quantity = max(listing.synced_quantity - quantity, 0)
    listing.save(update_fields=["synced_quantity"])


# --- Shipping ---

def report_shipment(order, carrier, tracking_number):
    """Report the shipment of an eBay order to eBay and mark it shipped locally."""
    _require_shippable(order)
    if not _is_simulated(order):  # eBay does not know simulated orders; they are only marked locally
        payload = _shipment_payload(order, carrier, tracking_number)
        call("POST", f"{ORDERS}/{order.ebay_order_id}/shipping_fulfillment", json=payload)
    order.fulfillment_status = Order.Fulfillment.SHIPPED
    order.shipping_carrier, order.tracking_number = carrier, tracking_number
    order.save(update_fields=["fulfillment_status", "shipping_carrier", "tracking_number"])
    return order


def _require_shippable(order):
    """Raise unless the order came from eBay, is not cancelled and has been paid."""
    if not order.ebay_order_id:
        raise ValidationError(NOT_FROM_EBAY)
    if order.fulfillment_status == Order.Fulfillment.CANCELLED:
        raise ValidationError(IS_CANCELLED)
    if order.payment_status != Order.Payment.PAID:
        raise ValidationError(NOT_PAID)


def _shipment_payload(order, carrier, tracking_number):
    """Build the createShippingFulfillment body covering all eBay line items of the order."""
    items = order.items.exclude(ebay_line_item_id="")
    return {
        "lineItems": [{"lineItemId": item.ebay_line_item_id, "quantity": item.quantity} for item in items],
        "shippedDate": _ebay_time(timezone.now()),
        "shippingCarrierCode": carrier,
        "trackingNumber": tracking_number,
    }
