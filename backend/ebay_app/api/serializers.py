"""Serializers for the eBay connection, the setup forms and the listings."""

from rest_framework import serializers

from ebay_app.models import EbayListing
from ebay_app.services.listings import listing_url
from products_app.models import Product

HANDLING_DAYS = [1, 2, 3, 4, 5, 10]
RETURN_DAYS = [14, 30, 60]
COST_PAYERS = ["BUYER", "SELLER"]


class ConnectFinishSerializer(serializers.Serializer):
    """Validate the redirect URL pasted after the eBay login."""

    redirect_url = serializers.CharField(max_length=4000)


class PolicyFormSerializer(serializers.Serializer):
    """Validate the shipping, return and payment settings of the setup form."""

    shipping_service = serializers.CharField(max_length=100)
    shipping_cost = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0)
    handling_days = serializers.ChoiceField(choices=HANDLING_DAYS)
    return_days = serializers.ChoiceField(choices=RETURN_DAYS)
    return_cost_payer = serializers.ChoiceField(choices=COST_PAYERS)


class PublishSerializer(serializers.Serializer):
    """Validate the eBay category and the aspect values chosen when listing a product."""

    category_id = serializers.CharField(max_length=16)
    category_name = serializers.CharField(max_length=255, allow_blank=True, default="")
    aspects = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        default=dict,
    )


class EbayListingSerializer(serializers.ModelSerializer):
    """Serialize the eBay listing of a product with its computed state."""

    state = serializers.ReadOnlyField()
    has_unsynced_changes = serializers.ReadOnlyField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = EbayListing
        fields = [
            "category_id", "category_name", "offer_id", "listing_id", "status", "state",
            "has_unsynced_changes", "last_synced", "sync_error", "url",
        ]

    def get_url(self, obj):
        """Return the public eBay page of the listing."""
        return listing_url(obj)


class ListingProductSerializer(serializers.ModelSerializer):
    """Serialize a product together with its eBay listing (null if never listed)."""

    image = serializers.SerializerMethodField()
    listing = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "title", "condition", "status", "sale_price", "quantity",
            "aspects", "image", "listing",
        ]

    def get_image(self, obj):
        """Return the URL of the main image, or None."""
        images = obj.images.all()
        return images[0].image.url if images else None

    def get_listing(self, obj):
        """Return the nested listing, or None if the product was never listed."""
        listing = getattr(obj, "ebay_listing", None)
        return EbayListingSerializer(listing).data if listing else None
