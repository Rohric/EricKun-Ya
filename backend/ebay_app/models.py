"""eBay-side state: account, policy ids, inventory locations, listings, category memory, hosted images."""

from django.db import models
from django.utils import timezone

from logistics_app.models import Warehouse
from products_app.models import Category, Product, ProductImage


class EbayAccount(models.Model):
    """Singleton with the encrypted OAuth tokens and the return/payment policy ids of the seller."""

    access_token = models.TextField(blank=True)  # Fernet-encrypted, see ebay_app.crypto
    access_expires_at = models.DateTimeField(null=True, blank=True)
    refresh_token = models.TextField(blank=True)  # Fernet-encrypted
    refresh_expires_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    oauth_state = models.CharField(max_length=64, blank=True)
    oauth_state_created_at = models.DateTimeField(null=True, blank=True)
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
        """Return True once return, payment and a default shipping policy exist on eBay."""
        if not (self.return_policy_id and self.payment_policy_id):
            return False
        default = EbayShippingProfile.default()
        return default is not None and bool(default.policy_id)


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


class EbayShippingProfile(models.Model):
    """One shipping (fulfillment) policy on eBay that can be chosen per listing."""

    name = models.CharField(max_length=60, unique=True)
    shipping_service = models.CharField(max_length=100, blank=True)
    shipping_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    handling_days = models.PositiveSmallIntegerField(default=1)
    policy_id = models.CharField(max_length=32, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "name"]

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.name} (Standard)" if self.is_default else self.name

    def save(self, *args, **kwargs):
        """Persist the profile and keep exactly one default."""
        others = EbayShippingProfile.objects.exclude(pk=self.pk)
        if not others.filter(is_default=True).exists():
            self.is_default = True  # the first or only profile is always the default
        super().save(*args, **kwargs)
        if self.is_default:
            others.filter(is_default=True).update(is_default=False)

    @classmethod
    def default(cls):
        """Return the default profile, or None if none exists yet."""
        return cls.objects.filter(is_default=True).first()


class EbayListing(models.Model):
    """eBay offer and listing of one product, plus what was last transferred."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        ONLINE = "online", "Online"
        ENDED = "ended", "Beendet"

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="ebay_listing")
    category_id = models.CharField(max_length=16)
    category_name = models.CharField(max_length=255, blank=True)
    # NULL means "use the default profile".
    shipping_profile = models.ForeignKey(
        EbayShippingProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="listings"
    )
    best_offer = models.BooleanField(default=False)
    offer_id = models.CharField(max_length=32, blank=True)
    listing_id = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)
    synced_quantity = models.PositiveIntegerField(default=0)
    last_synced = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True)
    # Facts read back from eBay: what buyers see and how many units eBay counts as sold.
    ebay_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sold_quantity = models.PositiveIntegerField(default=0)
    facts_synced_at = models.DateTimeField(null=True, blank=True)

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


class EbayCategoryMapping(models.Model):
    """Remember the eBay category last chosen for products of an internal category."""

    category = models.OneToOneField(Category, on_delete=models.CASCADE, related_name="ebay_mapping")
    ebay_category_id = models.CharField(max_length=16)
    ebay_category_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.category} → {self.ebay_category_name or self.ebay_category_id}"


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
