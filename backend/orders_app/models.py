"""Order and line-item models; an order groups items sold in one purchase."""

from decimal import Decimal

from django.db import models

from products_app.models import Product


class Order(models.Model):
    """Track a single sale and its shipping lifecycle."""

    class Fulfillment(models.TextChoices):
        OPEN = "open", "Offen"
        PACKED = "packed", "Verpackt"
        SHIPPED = "shipped", "Verschickt"
        DELIVERED = "delivered", "Zugestellt"

    sold_at = models.DateTimeField()
    fulfillment_status = models.CharField(
        max_length=16,
        choices=Fulfillment.choices,
        default=Fulfillment.OPEN,
    )
    tracking_number = models.CharField(max_length=64, blank=True)
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
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    sold_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.quantity} × {self.product.title}"

    @property
    def subtotal(self):
        """Return the line revenue (sold price times quantity)."""
        return self.sold_price * self.quantity

    @property
    def profit(self):
        """Return the line profit against the product's purchase price."""
        return (self.sold_price - self.product.purchase_price) * self.quantity
