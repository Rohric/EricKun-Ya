"""Platform-neutral product model: the source of truth for a sellable article."""

from django.db import models


class Category(models.Model):
    """Store an internal category; a self-referential parent forms the sub-category tree."""

    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]
        unique_together = ("parent", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        """Return the readable category path (parent › child)."""
        return f"{self.parent} › {self.name}" if self.parent_id else self.name


class Product(models.Model):
    """Store the platform-neutral truth about a sellable article."""

    class Condition(models.TextChoices):
        """List the gradings an article can have, from new to defective."""

        NEW = "new", "Neu"
        LIKE_NEW = "like_new", "Wie neu"
        VERY_GOOD = "very_good", "Sehr gut"
        GOOD = "good", "Gut"
        ACCEPTABLE = "acceptable", "Akzeptabel"
        FOR_PARTS = "for_parts", "Defekt / Ersatzteile"

    class Status(models.TextChoices):
        """List the stages of an article from available to archived."""

        AVAILABLE = "available", "Verfügbar"
        RESERVED = "reserved", "Reserviert"
        SOLD = "sold", "Verkauft"
        ARCHIVED = "archived", "Archiviert"

    sku = models.CharField(max_length=64, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    condition = models.CharField(
        max_length=16,
        choices=Condition.choices,
        default=Condition.GOOD,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    aspects = models.JSONField(default=dict, blank=True)
    purchase_date = models.DateField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.sku} – {self.title}"

    def save(self, *args, **kwargs):
        """Assign the next internal article number on first save, then persist."""
        from products_app.utils import generate_sku  # local import avoids a circular import

        if not self.sku:
            self.sku = generate_sku()
        super().save(*args, **kwargs)

    @property
    def profit(self):
        """Return the per-unit margin between sale and purchase price."""
        return self.sale_price - self.purchase_price

    @property
    def category_path(self):
        """Return the readable category path, or an empty string if unset."""
        return str(self.category) if self.category_id else ""


class SkuSequence(models.Model):
    """Count the internal article numbers handed out, so that none is ever used twice."""

    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"Letzte Artikelnummer: {self.last_number}"


def product_image_path(instance, filename):
    """Return the upload path for a product image, grouped in a per-SKU folder."""
    return f"products/{instance.product.sku}/{filename}"


class ProductImage(models.Model):
    """Store one image of a product; ordered, position 0 is the main image."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_path)
    position = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.product.sku} #{self.position}"
