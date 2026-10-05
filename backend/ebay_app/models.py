"""eBay-side state: account connection, business policy ids and synced inventory locations."""

from django.db import models
from django.utils import timezone

from logistics_app.models import Warehouse


class EbayAccount(models.Model):
    """Singleton with the encrypted OAuth tokens and the business policy ids of the seller."""

    access_token = models.TextField(blank=True)  # Fernet-encrypted, see ebay_app.crypto
    access_expires_at = models.DateTimeField(null=True, blank=True)
    refresh_token = models.TextField(blank=True)  # Fernet-encrypted
    refresh_expires_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    oauth_state = models.CharField(max_length=64, blank=True)
    oauth_state_created_at = models.DateTimeField(null=True, blank=True)
    fulfillment_policy_id = models.CharField(max_length=32, blank=True)
    return_policy_id = models.CharField(max_length=32, blank=True)
    payment_policy_id = models.CharField(max_length=32, blank=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return "eBay-Konto (verbunden)" if self.is_connected else "eBay-Konto (nicht verbunden)"

    def save(self, *args, **kwargs):
        """Force the singleton primary key so only one row can exist."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Return the singleton row, creating it on first access."""
        account, _ = cls.objects.get_or_create(pk=1)
        return account

    @property
    def is_connected(self):
        """Return True while a refresh token exists and has not expired."""
        if not self.refresh_token or not self.refresh_expires_at:
            return False
        return self.refresh_expires_at > timezone.now()

    @property
    def has_policies(self):
        """Return True once all three business policies exist on eBay."""
        return all([self.fulfillment_policy_id, self.return_policy_id, self.payment_policy_id])


class EbayLocation(models.Model):
    """eBay inventory location (merchantLocationKey) that mirrors a warehouse."""

    warehouse = models.OneToOneField(Warehouse, on_delete=models.CASCADE, related_name="ebay_location")
    merchant_location_key = models.CharField(max_length=36, unique=True)
    last_synced = models.DateTimeField()

    def __str__(self):
        """Return a readable label for admin and shell."""
        return self.merchant_location_key

    @property
    def needs_resync(self):
        """Return True if the warehouse changed after its last transfer to eBay."""
        return self.warehouse.updated_at > self.last_synced
