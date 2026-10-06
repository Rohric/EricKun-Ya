"""Simulate eBay sales in the sandbox, because the sandbox checkout does not create orders."""

import random
import secrets

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException

from ebay_app.models import EbayListing
from ebay_app.services import listings, orders
from ebay_app.services.orders import SIMULATED_PREFIX
from orders_app.models import Order
from products_app.models import Product

BUYERS = [
    {"username": "testuser_buyer-edwin", "name": "Edwin Beispiel", "street": "Kaufweg 5", "zip": "10115", "city": "Berlin"},
    {"username": "testuser_buyer-mara", "name": "Mara Muster", "street": "Hafenstraße 12", "zip": "20457", "city": "Hamburg"},
    {"username": "testuser_buyer-jonas", "name": "Jonas Probe", "street": "Am Markt 3", "zip": "50667", "city": "Köln"},
]
NOT_SANDBOX = "Verkäufe dürfen nur in der Sandbox simuliert werden (EBAY_ENV ist nicht „sandbox“)."
UNKNOWN_SKU = "Es gibt keinen Artikel mit der Artikelnummer {sku}."
NOT_ENOUGH = "Von „{title}“ sind nur {available} Stück verfügbar."
NOT_SIMULATED = "Bestellung {pk} ist keine simulierte eBay-Bestellung."


class SimulationError(Exception):
    """A simulated sale, payment or cancellation cannot be carried out."""


def simulate_sale(sku, quantity=1, paid=True):
    """Create an order as if eBay had reported a sale of the product; return the order."""
    _require_sandbox()
    product = _product_with_stock(sku, quantity)
    payload = sale_payload(product, quantity, paid)
    orders.import_payloads([payload])
    _push_remaining_stock(product)
    return Order.objects.get(ebay_order_id=payload["orderId"])


def simulate_payment(order_pk):
    """Mark a simulated order as paid, as if eBay had reported the payment; return the order."""
    return _report_change(order_pk, {"orderPaymentStatus": "PAID", "cancelStatus": {"cancelState": "NONE_REQUESTED"}})


def simulate_cancellation(order_pk):
    """Cancel a simulated order as if eBay had reported the cancellation; return the order."""
    return _report_change(order_pk, {"cancelStatus": {"cancelState": "CANCELED"}})


def _report_change(order_pk, change):
    """Send a follow-up payload for a simulated order through the normal import."""
    _require_sandbox()
    order = Order.objects.filter(pk=order_pk, ebay_order_id__startswith=SIMULATED_PREFIX).first()
    if order is None:
        raise SimulationError(NOT_SIMULATED.format(pk=order_pk))
    orders.import_payloads([{"orderId": order.ebay_order_id, **change}])
    order.refresh_from_db()
    return order


def sale_payload(product, quantity, paid=True):
    """Build an order in the shape of eBay's getOrders response for one product."""
    buyer = random.choice(BUYERS)
    return {
        "orderId": f"{SIMULATED_PREFIX}{timezone.now():%Y%m%d-%H%M%S}-{secrets.token_hex(2).upper()}",
        "creationDate": timezone.now().isoformat(),
        "orderPaymentStatus": "PAID" if paid else "PENDING",
        "orderFulfillmentStatus": "NOT_STARTED",
        "cancelStatus": {"cancelState": "NONE_REQUESTED"},
        "buyer": {"username": buyer["username"]},
        "fulfillmentStartInstructions": [{"shippingStep": {"shipTo": _ship_to(buyer)}}],
        "lineItems": [_line_item(product, quantity)],
    }


def _ship_to(buyer):
    """Return the delivery address block of a simulated buyer."""
    address = {"addressLine1": buyer["street"], "postalCode": buyer["zip"], "city": buyer["city"], "countryCode": "DE"}
    return {"fullName": buyer["name"], "contactAddress": address}


def _line_item(product, quantity):
    """Return one line item; like eBay, the cost covers the whole line."""
    return {
        "lineItemId": f"{SIMULATED_PREFIX}LI-{secrets.token_hex(4).upper()}",
        "sku": product.sku,
        "title": product.title,
        "quantity": quantity,
        "lineItemCost": {"value": f"{product.sale_price * quantity:.2f}", "currency": "EUR"},
    }


def _require_sandbox():
    """Refuse to invent orders outside the sandbox."""
    if settings.EBAY_ENV != "sandbox":
        raise SimulationError(NOT_SANDBOX)


def _product_with_stock(sku, quantity):
    """Return the product for a SKU, or raise if it is unknown or lacks stock."""
    product = Product.objects.filter(sku=sku).first()
    if product is None:
        raise SimulationError(UNKNOWN_SKU.format(sku=sku))
    if quantity < 1 or quantity > product.quantity:
        raise SimulationError(NOT_ENOUGH.format(title=product.title, available=product.quantity))
    return product


def _push_remaining_stock(product):
    """Send the remaining quantity to eBay, because only a real sale lowers eBay's own stock."""
    product.refresh_from_db()
    online = EbayListing.objects.filter(product=product, status=EbayListing.Status.ONLINE).exists()
    if not online or product.quantity < 1:
        return  # a sold-out product's listing is ended by the product signal
    try:
        listings.sync(product)
    except APIException:
        pass  # the reason is stored on the listing and shown in the eBay tab
