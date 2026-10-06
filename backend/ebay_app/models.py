"""eBay-side state: account, policy ids, inventory locations, listings, category memory, hosted images."""

from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone

from logistics_app.models import Warehouse
from products_app.models import Category, Product, ProductImage


class EbayAccount(models.Model):
    """Store the seller's encrypted OAuth tokens and the return/payment policy ids (single row)."""

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
    """Remember the eBay inventory location (merchantLocationKey) that mirrors a warehouse."""

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
    """Store one shipping (fulfillment) policy on eBay that can be chosen per listing."""

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
        if not self._other_defaults().exists():
            self.is_default = True  # the first or only profile is always the default
        super().save(*args, **kwargs)
        if self.is_default:
            self._other_defaults().update(is_default=False)

    def _other_defaults(self):
        """Return the other default profiles (asked anew each time: a new profile has no pk before saving)."""
        return EbayShippingProfile.objects.exclude(pk=self.pk).filter(is_default=True)

    @classmethod
    def default(cls):
        """Return the default profile, or None if none exists yet."""
        return cls.objects.filter(is_default=True).first()


class EbayListing(models.Model):
    """Mirror one listing on eBay; it exists on its own and belongs to at most one product."""

    class Status(models.TextChoices):
        """List the stages of a listing on eBay."""

        DRAFT = "draft", "Entwurf"
        ONLINE = "online", "Online"
        ENDED = "ended", "Beendet"

    # NULL means "not assigned yet": the listing was found on eBay and waits in the assignment view.
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, null=True, blank=True, related_name="ebay_listing"
    )
    # The article number eBay knows the listing by. Ours for listings we create or convert,
    # a foreign one where eBay does not let an existing entry be renamed.
    sku = models.CharField(max_length=64, blank=True, db_index=True)
    category_id = models.CharField(max_length=16, blank=True)
    category_name = models.CharField(max_length=255, blank=True)
    # NULL means "use the default profile".
    shipping_profile = models.ForeignKey(
        EbayShippingProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="listings"
    )
    best_offer = models.BooleanField(default=False)
    offer_id = models.CharField(max_length=32, blank=True)
    listing_id = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)
    # What eBay currently holds: written after every transfer and by the pull from eBay.
    title = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    synced_quantity = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=500, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True)
    # Flags of listings found on eBay.
    needs_migration = models.BooleanField(default=False)  # created outside the Inventory API
    supported = models.BooleanField(default=True)  # False for auctions and listings with variations
    ignored = models.BooleanField(default=False)  # hidden from the assignment view
    # Facts read back from eBay: what buyers see and how many units eBay counts as sold.
    ebay_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sold_quantity = models.PositiveIntegerField(default=0)
    facts_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # Legacy listings may share a number on eBay; everything else is unique per number.
            models.UniqueConstraint(
                fields=["sku"], condition=~Q(sku="") & Q(needs_migration=False), name="unique_ebay_listing_sku"
            ),
        ]

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.sku or self.listing_id} ({self.get_status_display()})"

    @property
    def has_unsynced_changes(self):
        """Return True if the online listing no longer matches its product (data, stock or price)."""
        if self.product_id is None or self.status != self.Status.ONLINE or self.last_synced is None:
            return False
        # Stock bookings skip updated_at, so stock and price are compared with what eBay holds.
        if self.product.quantity != self.synced_quantity or self._price_differs():
            return True
        return self.product.updated_at > self.last_synced

    def _price_differs(self):
        """Return True if eBay holds another price than the product (unknown counts as equal)."""
        return self.price is not None and Decimal(self.price) != Decimal(self.product.sale_price)

    @property
    def state(self):
        """Return the state shown in the UI; the stored status comes last."""
        if self.ignored:
            return "ignored"
        if self.product_id is None:
            return "unassigned"
        if self.sync_error:
            return "error"
        return "changed" if self.has_unsynced_changes else self.status


class EbayCategoryMapping(models.Model):
    """Remember the eBay category last chosen for products of an internal category."""

    category = models.OneToOneField(Category, on_delete=models.CASCADE, related_name="ebay_mapping")
    ebay_category_id = models.CharField(max_length=16)
    ebay_category_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        """Return a readable label for admin and shell."""
        return f"{self.category} → {self.ebay_category_name or self.ebay_category_id}"


class EbayImage(models.Model):
    """Remember the URL of a product image hosted by eBay, so each file is uploaded only once."""

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
