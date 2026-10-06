"""Turn the single shipping policy of the account into the first shipping profile."""

from django.db import migrations

PROFILE_NAME = "Standard"


def adopt_policy(apps, schema_editor):
    """Create the default profile from the account's policy id and assign it to all listings."""
    account = apps.get_model("ebay_app", "EbayAccount").objects.filter(pk=1).first()
    if account is None or not account.fulfillment_policy_id:
        return
    # Service, cost and handling time live on eBay only; they are read back on first use.
    profile = apps.get_model("ebay_app", "EbayShippingProfile").objects.create(
        name=PROFILE_NAME, policy_id=account.fulfillment_policy_id, is_default=True,
    )
    apps.get_model("ebay_app", "EbayListing").objects.update(shipping_profile=profile)


def restore_policy(apps, schema_editor):
    """Write the default profile's policy id back to the account."""
    profile = apps.get_model("ebay_app", "EbayShippingProfile").objects.filter(is_default=True).first()
    if profile is None:
        return
    apps.get_model("ebay_app", "EbayAccount").objects.filter(pk=1).update(fulfillment_policy_id=profile.policy_id)
    apps.get_model("ebay_app", "EbayListing").objects.update(shipping_profile=None)


class Migration(migrations.Migration):

    dependencies = [
        ("ebay_app", "0004_shipping_profiles_and_listing_facts"),
    ]

    operations = [
        migrations.RunPython(adopt_policy, restore_policy),
    ]
