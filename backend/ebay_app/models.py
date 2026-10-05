"""eBay-side state: account connection, policy ids, inventory locations, listings and hosted images."""

from django.db import models
from django.utils import timezone

from logistics_app.models import Warehouse
from products_app.models import Product, ProductImage


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
    orders_synced_at = models.DateTimeField(null=True, blank=True)

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


class EbayListing(models.Model):
    """eBay offer and listing of one product, plus what was last transferred."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        ONLINE = "online", "Online"
        ENDED = "ended", "Beendet"

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="ebay_listing")
    category_id = models.CharField(max_length=16)
    category_name = models.CharField(max_length=255, blank=True)
    offer_id = models.CharField(max_length=32, blank=True)
    listing_id = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)
    synced_quantity = models.PositiveIntegerField(default=0)
    last_synced = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.product.sku} ({self.get_status_display()})"

    @property
    def has_unsynced_changes(self):
        """Return True if the online listing no longer matches the product."""
        if self.status != self.Status.ONLINE or self.last_synced is None:
            return False
        # Stock bookings skip updated_at, so the quantity is compared separately.
        return self.product.updated_at > self.last_synced or self.product.quantity != self.synced_quantity

    @property
    def state(self):
        """Return the state shown in the UI: error and changed outrank the stored status."""
        if self.sync_error:
            return "error"
        if self.has_unsynced_changes:
            return "changed"
        return self.status


class EbayImage(models.Model):
    """URL of a product image hosted by eBay, so each file is uploaded only once."""

    image = models.OneToOneField(ProductImage, on_delete=models.CASCADE, related_name="ebay_image")
    eps_url = models.URLField(max_length=500)
    source_name = models.CharField(max_length=255)  # file the URL was created from
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return self.source_name

    def is_valid_for(self, image):
        """Return True if the hosted copy still belongs to the image's file and has not expired."""
        if self.source_name != image.image.name:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()
