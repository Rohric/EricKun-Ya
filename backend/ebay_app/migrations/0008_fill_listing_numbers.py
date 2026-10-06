"""Give every existing listing the article number eBay knows it by: the one of its product."""

from django.db import migrations


def fill_numbers(apps, schema_editor):
    """Copy the product's number and title onto its listing (the price eBay holds stays unknown)."""
    listings = apps.get_model("ebay_app", "EbayListing").objects.select_related("product")
    for listing in listings.filter(sku="", product__isnull=False):
        listing.sku, listing.title = listing.product.sku, listing.product.title
        listing.save(update_fields=["sku", "title"])


def clear_numbers(apps, schema_editor):
    """Remove the copied numbers again; listings without product cannot exist before this change."""
    listings = apps.get_model("ebay_app", "EbayListing").objects
    listings.filter(product__isnull=True).delete()
    listings.update(sku="", title="")


class Migration(migrations.Migration):

    dependencies = [
        ("ebay_app", "0007_independent_listings"),
    ]

    operations = [
        migrations.RunPython(fill_numbers, clear_numbers),
    ]
