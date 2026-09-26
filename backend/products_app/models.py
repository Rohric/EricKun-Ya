"""Platform-neutral product model: the source of truth for a sellable article."""

from django.db import models


class Product(models.Model):
    """Store the platform-neutral truth about a sellable article."""

    class Condition(models.TextChoices):
        NEW = "new", "Neu"
        LIKE_NEW = "like_new", "Wie neu"
        VERY_GOOD = "very_good", "Sehr gut"
        GOOD = "good", "Gut"
        ACCEPTABLE = "acceptable", "Akzeptabel"
        FOR_PARTS = "for_parts", "Defekt / Ersatzteile"

    sku = models.CharField(max_length=64, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    condition = models.CharField(
        max_length=16,
        choices=Condition.choices,
        default=Condition.GOOD,
    )
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    aspects = models.JSONField(default=dict, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.sku} – {self.title}"

    def save(self, *args, **kwargs):
        """Assign a generated SKU on first save, then persist."""
        from products_app.utils import generate_sku  # local import avoids a circular import

        if not self.sku:
            self.sku = generate_sku()
        super().save(*args, **kwargs)

    @property
    def profit(self):
        """Return the per-unit margin between sale and purchase price."""
        return self.sale_price - self.purchase_price
