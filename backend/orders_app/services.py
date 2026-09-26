"""Business logic for orders: stock synchronisation and cancellation."""

from products_app.models import Product


def apply_stock_change(product, delta):
    """Adjust a product's stock by delta and keep its sale status in sync."""
    if product is None:
        return
    product.quantity = max(product.quantity + delta, 0)
    if product.quantity == 0 and product.status in (Product.Status.AVAILABLE, Product.Status.RESERVED):
        product.status = Product.Status.SOLD
    elif product.quantity > 0 and product.status == Product.Status.SOLD:
        product.status = Product.Status.AVAILABLE
    product.save(update_fields=["quantity", "status"])


def sync_stock(order, sign):
    """Apply (sign × quantity) to the stock of every line item's product."""
    for item in order.items.select_related("product"):
        apply_stock_change(item.product, sign * item.quantity)


def cancel_order(order, item_action):
    """Cancel an order, restock its items and apply the chosen product action."""
    sync_stock(order, sign=1)
    order.fulfillment_status = order.Fulfillment.CANCELLED
    order.save(update_fields=["fulfillment_status"])
    _apply_item_action(order, item_action)


def _apply_item_action(order, item_action):
    """Set each product available/archived, or delete it, after a cancellation."""
    for item in order.items.select_related("product"):
        if item.product is None:
            continue
        if item_action == "delete":
            item.product.delete()
        elif item_action == "archive":
            _set_status(item.product, Product.Status.ARCHIVED)
        else:
            _set_status(item.product, Product.Status.AVAILABLE)


def _set_status(product, status):
    """Persist a single product's status."""
    product.status = status
    product.save(update_fields=["status"])
