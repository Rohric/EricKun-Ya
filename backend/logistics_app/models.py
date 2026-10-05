"""Storage locations: where goods are kept and shipped from."""

from django.db import models


class Warehouse(models.Model):
    """Store a physical storage location; exactly one is the default ship-from address."""

    name = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=20)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=2, default="DE")  # ISO 3166-1 alpha-2 code
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "name"]

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.name} ({self.city})"

    def save(self, *args, **kwargs):
        """Persist the warehouse and keep exactly one default."""
        if not Warehouse.objects.exclude(pk=self.pk).filter(is_default=True).exists():
            self.is_default = True  # the first or only warehouse is always the default
        super().save(*args, **kwargs)
        if self.is_default:
            Warehouse.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    @classmethod
    def default(cls):
        """Return the default warehouse, or None if none exists yet."""
        return cls.objects.filter(is_default=True).first()
