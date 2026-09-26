"""Financial planning models: goals and the adjustable reserve setting."""

from decimal import Decimal

from django.conf import settings
from django.db import models


class Goal(models.Model):
    """Store a revenue or profit target over a period or fixed date range."""

    class Metric(models.TextChoices):
        REVENUE = "revenue", "Umsatz"
        PROFIT = "profit", "Gewinn"

    class Period(models.TextChoices):
        MONTHLY = "monthly", "Monatlich"
        YEARLY = "yearly", "Jährlich"
        TOTAL = "total", "Gesamt"

    title = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    metric = models.CharField(max_length=16, choices=Metric.choices, default=Metric.REVENUE)
    period = models.CharField(max_length=16, choices=Period.choices, default=Period.YEARLY)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.title} ({self.target_amount})"


class FinanceSettings(models.Model):
    """Singleton holding the adjustable tax-reserve rate in percent."""

    tax_reserve_rate = models.DecimalField(max_digits=5, decimal_places=2, default=25)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"Rücklagensatz: {self.tax_reserve_rate} %"

    def save(self, *args, **kwargs):
        """Force the singleton primary key so only one row can exist."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Return the singleton row, creating it with the configured default."""
        default = Decimal(str(getattr(settings, "TAX_RESERVE_RATE", "25")))
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"tax_reserve_rate": default})
        return obj
