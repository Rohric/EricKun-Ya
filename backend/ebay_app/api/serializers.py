"""Serializers for the eBay connection, the setup forms, the listings and the sales."""

from rest_framework import serializers

from ebay_app.models import EbayListing, EbayShippingProfile
from ebay_app.services import assignment
from ebay_app.services.listings import CHANNEL, CHANNEL_LABEL, listing_url
from ebay_app.services.orders import CARRIERS
from products_app.models import Product

HANDLING_DAYS = [1, 2, 3, 4, 5, 10]
RETURN_DAYS = [14, 30, 60]
COST_PAYERS = ["BUYER", "SELLER"]
BAD_TRACKING = "Die Trackingnummer darf nur Buchstaben und Ziffern enthalten (ohne Leerzeichen)."


class ConnectFinishSerializer(serializers.Serializer):
    """Validate the redirect URL pasted after the eBay login."""

    redirect_url = serializers.CharField(max_length=4000)


class PolicyFormSerializer(serializers.Serializer):
    """Validate the return settings of the setup form (the payment policy has no options)."""

    return_days = serializers.ChoiceField(choices=RETURN_DAYS)
    return_cost_payer = serializers.ChoiceField(choices=COST_PAYERS)


class ShippingProfileSerializer(serializers.ModelSerializer):
    """Serialize a shipping profile; its eBay policy id and usage are read-only."""

    handling_days = serializers.ChoiceField(choices=HANDLING_DAYS)
    shipping_service = serializers.CharField(max_length=100)
    shipping_cost = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0)
    listing_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = EbayShippingProfile
        fields = [
            "id", "name", "shipping_service", "shipping_cost", "handling_days",
            "is_default", "policy_id", "listing_count",
        ]
        read_only_fields = ["is_default", "policy_id"]


class PublishSerializer(serializers.Serializer):
    """Validate the category, aspects and options chosen when listing a product."""

    category_id = serializers.CharField(max_length=16)
    category_name = serializers.CharField(max_length=255, allow_blank=True, default="")
    aspects = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        default=dict,
    )
    shipping_profile = serializers.PrimaryKeyRelatedField(
        queryset=EbayShippingProfile.objects.all(), allow_null=True, default=None,
    )
    best_offer = serializers.BooleanField(default=False)

    def listing_arguments(self):
        """Return (category, aspects, options) in the shape the listing service expects."""
        data = self.validated_data
        category = {"id": data["category_id"], "name": data["category_name"]}
        options = {"shipping_profile": data["shipping_profile"], "best_offer": data["best_offer"]}
        return category, data["aspects"], options


class ShipmentSerializer(serializers.Serializer):
    """Validate the carrier and tracking number reported to eBay."""

    carrier = serializers.ChoiceField(choices=[carrier["code"] for carrier in CARRIERS])
    tracking_number = serializers.RegexField(
        r"^[A-Za-z0-9]+$",
        max_length=64,
        error_messages={"invalid": BAD_TRACKING},
    )


class EbayListingSerializer(serializers.ModelSerializer):
    """Serialize the eBay listing of a product with its computed state and eBay facts."""

    state = serializers.ReadOnlyField()
    has_unsynced_changes = serializers.ReadOnlyField()
    url = serializers.SerializerMethodField()
    shipping_profile_name = serializers.SerializerMethodField()

    class Meta:
        model = EbayListing
        fields = [
            "sku", "category_id", "category_name", "shipping_profile", "shipping_profile_name", "best_offer",
            "offer_id", "listing_id", "status", "state", "has_unsynced_changes", "last_synced",
            "sync_error", "url", "ebay_price", "sold_quantity", "facts_synced_at",
        ]

    def get_url(self, obj):
        """Return the public eBay page of the listing."""
        return listing_url(obj)

    def get_shipping_profile_name(self, obj):
        """Return the name of the chosen profile, or an empty string for the default one."""
        return obj.shipping_profile.name if obj.shipping_profile_id else ""


class LinkSerializer(serializers.Serializer):
    """Validate the article an unassigned listing is linked to."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())


class IgnoreSerializer(serializers.Serializer):
    """Validate whether an unassigned listing is hidden (default) or shown again."""

    ignored = serializers.BooleanField(default=True)


class UnassignedListingSerializer(serializers.ModelSerializer):
    """Serialize a listing without article in the format every sales channel delivers."""

    channel = serializers.SerializerMethodField()
    channel_label = serializers.SerializerMethodField()
    channel_sku = serializers.CharField(source="sku")
    quantity = serializers.IntegerField(source="synced_quantity")
    image = serializers.CharField(source="image_url")
    url = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    suggestion = serializers.SerializerMethodField()

    class Meta:
        model = EbayListing
        fields = [
            "id", "channel", "channel_label", "channel_sku", "listing_id", "title", "price", "quantity",
            "image", "url", "status", "ignored", "supported", "needs_migration", "notes", "suggestion",
        ]

    def get_channel(self, obj):
        """Return the key of the sales channel."""
        return CHANNEL

    def get_channel_label(self, obj):
        """Return the display name of the sales channel."""
        return CHANNEL_LABEL

    def get_url(self, obj):
        """Return the public eBay page of the listing."""
        return listing_url(obj)

    def get_notes(self, obj):
        """Return the hints for this listing, e.g. that it is converted when it is linked."""
        return assignment.notes(obj)

    def get_suggestion(self, obj):
        """Return the free article that fits best as {id, sku, title}, or None."""
        product = assignment.suggest(obj, self.context.get("products", []))
        return {"id": product.id, "sku": product.sku, "title": product.title} if product else None


class ListingProductSerializer(serializers.ModelSerializer):
    """Serialize a product together with its eBay listing (null if never listed)."""

    image = serializers.SerializerMethodField()
    listing = serializers.SerializerMethodField()
    remembered_category = serializers.SerializerMethodField()
    category_path = serializers.ReadOnlyField()
    sold_units = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Product
        fields = [
            "id", "sku", "title", "condition", "status", "sale_price", "quantity", "aspects",
            "category_path", "image", "listing", "remembered_category", "sold_units",
        ]

    def get_image(self, obj):
        """Return the URL of the main image, or None."""
        images = obj.images.all()
        return images[0].image.url if images else None

    def get_listing(self, obj):
        """Return the nested listing, or None if the product was never listed."""
        listing = getattr(obj, "ebay_listing", None)
        return EbayListingSerializer(listing).data if listing else None

    def get_remembered_category(self, obj):
        """Return the eBay category last used for the product's internal category, or None."""
        mapping = getattr(obj.category, "ebay_mapping", None) if obj.category_id else None
        if mapping is None:
            return None
        return {"id": mapping.ebay_category_id, "name": mapping.ebay_category_name}
