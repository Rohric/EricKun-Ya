"""Side effects for the eBay app: keep listings in step with product changes."""

from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from ebay_app.models import EbayListing
from ebay_app.services import listings
from products_app.models import Product


@receiver(post_save, sender=Product)
def end_listing_of_unsellable_product(sender, instance, **kwargs):
    """End the eBay listing once the product is sold out or archived."""
    # After the commit, so a rolled-back order never ends a listing.
    transaction.on_commit(lambda: listings.end_if_unsellable(instance))


@receiver(pre_delete, sender=Product)
def remove_deleted_product_from_ebay(sender, instance, **kwargs):
    """Remove the inventory item on eBay when a listed product is deleted."""
    if not EbayListing.objects.filter(product=instance).exists():
        return
    sku = instance.sku
    transaction.on_commit(lambda: listings.remove_item(sku))
