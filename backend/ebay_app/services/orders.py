"""Bring eBay sales into orders_app and report shipments back to eBay."""

from datetime import timedelta, timezone as dt_timezone
from decimal import Decimal

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


# --- Import ---

def import_orders():
    """Fetch new and changed eBay orders; return what was created and cancelled."""
    account = EbayAccount.load()
    started = timezone.now()
    result = {"created": 0, "cancelled": 0, "unknown_skus": []}
    for payload in _changed_orders(account.orders_synced_at):
        _import_one(payload, result)
    account.orders_synced_at = started
    account.save(update_fields=["orders_synced_at"])
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
    """Create a new paid order, or cancel a known one that eBay shows as cancelled."""
    order = Order.objects.filter(ebay_order_id=payload["orderId"]).first()
    cancelled = (payload.get("cancelStatus") or {}).get("cancelState") == "CANCELED"
    if order is None and not cancelled and payload.get("orderPaymentStatus") in PAID_STATES:
        _create_order(payload, result)
        result["created"] += 1
    elif order and cancelled and order.fulfillment_status != Order.Fulfillment.CANCELLED:
        cancel_order(order, Cancellation.ItemAction.AVAILABLE, CANCELLED_ON_EBAY, Cancellation.Source.EBAY)
        result["cancelled"] += 1


def _create_order(payload, result):
    """Create the local order with buyer data and items, then book the stock."""
    order = Order.objects.create(
        ebay_order_id=payload["orderId"],
        sold_at=parse_datetime(payload["creationDate"]),
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
    """Create one line item; an unknown SKU is kept without product and reported."""
    product = Product.objects.filter(sku=line.get("sku") or "").first()
    quantity = int(line.get("quantity") or 1)
    if product is None:
        result["unknown_skus"].append(line.get("sku") or line.get("title", "?"))
    else:
        _mirror_sold_quantity(product, quantity)
    OrderItem.objects.create(
        order=order, product=product, quantity=quantity,
        sold_price=_unit_price(line, quantity), ebay_line_item_id=line.get("lineItemId", ""),
    )


def _unit_price(line, quantity):
    """Return the price per unit; eBay reports the cost of the whole line."""
    total = Decimal((line.get("lineItemCost") or {}).get("value", "0"))
    return (total / quantity).quantize(Decimal("0.01"))


def _mirror_sold_quantity(product, quantity):
    """Lower the listing's synced quantity, because eBay already reduced its own stock."""
    listing = EbayListing.objects.filter(product=product).first()
    if listing is None:
        return
    listing.synced_quantity = max(listing.synced_quantity - quantity, 0)
    listing.save(update_fields=["synced_quantity"])


# --- Shipping ---

def report_shipment(order, carrier, tracking_number):
    """Report the shipment of an eBay order to eBay and mark it shipped locally."""
    if not order.ebay_order_id:
        raise ValidationError(NOT_FROM_EBAY)
    if order.fulfillment_status == Order.Fulfillment.CANCELLED:
        raise ValidationError(IS_CANCELLED)
    payload = _shipment_payload(order, carrier, tracking_number)
    call("POST", f"{ORDERS}/{order.ebay_order_id}/shipping_fulfillment", json=payload)
    order.fulfillment_status = Order.Fulfillment.SHIPPED
    order.shipping_carrier, order.tracking_number = carrier, tracking_number
    order.save(update_fields=["fulfillment_status", "shipping_carrier", "tracking_number"])
    return order


def _shipment_payload(order, carrier, tracking_number):
    """Build the createShippingFulfillment body covering all eBay line items of the order."""
    items = order.items.exclude(ebay_line_item_id="")
    return {
        "lineItems": [{"lineItemId": item.ebay_line_item_id, "quantity": item.quantity} for item in items],
        "shippedDate": _ebay_time(timezone.now()),
        "shippingCarrierCode": carrier,
        "trackingNumber": tracking_number,
    }
