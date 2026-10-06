"""Order, line-item and cancellation models; an order groups items sold in one purchase."""

from decimal import Decimal

from django.db import models

from products_app.models import Product


class Order(models.Model):
    """Track a single sale, its buyer/shipping details and its fulfillment lifecycle."""

    class Fulfillment(models.TextChoices):
        """List the steps of an order from open to delivered, returned or cancelled."""

        OPEN = "open", "Offen"
        PACKED = "packed", "Verpackt"
        SHIPPED = "shipped", "Verschickt"
        DELIVERED = "delivered", "Zugestellt"
        IN_RETURN = "in_return", "In Reklamation"
        CANCELLED = "cancelled", "Storniert"

    class Payment(models.TextChoices):
        """Tell whether the buyer has paid."""

        PAID = "paid", "Bezahlt"
        PENDING = "pending", "Zahlung offen"

    sold_at = models.DateTimeField(db_index=True)
    fulfillment_status = models.CharField(
        max_length=16,
        choices=Fulfillment.choices,
        default=Fulfillment.OPEN,
    )
    payment_status = models.CharField(max_length=8, choices=Payment.choices, default=Payment.PAID)
    tracking_number = models.CharField(max_length=64, blank=True)
    shipping_carrier = models.CharField(max_length=40, blank=True)
    # Buyer / shipping details: entered manually or filled by the eBay order import.
    buyer_name = models.CharField(max_length=255, blank=True)
    ship_street = models.CharField(max_length=255, blank=True)
    ship_zip = models.CharField(max_length=20, blank=True)
    ship_city = models.CharField(max_length=120, blank=True)
    ship_country = models.CharField(max_length=80, blank=True)
    ebay_username = models.CharField(max_length=120, blank=True)
    # Id of the sale on eBay; NULL for manual orders so the unique check ignores them.
    ebay_order_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    return_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"Order #{self.pk} ({self.sold_at:%Y-%m-%d})"

    @property
    def total_revenue(self):
        """Return the summed sale price across all line items."""
        return sum((item.subtotal for item in self.items.all()), Decimal("0"))

    @property
    def total_profit(self):
        """Return the summed profit across all line items."""
        return sum((item.profit for item in self.items.all()), Decimal("0"))


class OrderItem(models.Model):
    """Track one product position within an order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, related_name="order_items"
    )
    sold_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    ebay_line_item_id = models.CharField(max_length=40, blank=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        title = self.product.title if self.product_id else "(gelöschter Artikel)"
        return f"{self.quantity} × {title}"

    @property
    def subtotal(self):
        """Return the line revenue (sold price times quantity)."""
        return self.sold_price * self.quantity

    @property
    def profit(self):
        """Return the line profit against the product's purchase price (0 if deleted)."""
        if not self.product_id:
            return Decimal("0")
        return (self.sold_price - self.product.purchase_price) * self.quantity


class Cancellation(models.Model):
    """Record why and how an order was cancelled."""

    class Source(models.TextChoices):
        """Tell who cancelled the order: the seller by hand, or the marketplace."""

        MANUAL = "manual", "Manuell"
        EBAY = "ebay", "eBay"

    class ItemAction(models.TextChoices):
        """List what can happen to the products of a cancelled order."""

        AVAILABLE = "available", "Wieder verfügbar"
        ARCHIVE = "archive", "Ins Archiv"
        DELETE = "delete", "Artikel gelöscht"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="cancellation")
    reason = models.TextField(blank=True)
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.MANUAL)
    item_action = models.CharField(max_length=10, choices=ItemAction.choices, default=ItemAction.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"Storno Order #{self.order_id} ({self.get_source_display()})"
