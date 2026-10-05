"""Mirror the default warehouse to eBay as an inventory location (merchantLocationKey)."""

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ebay_app.models import EbayLocation
from ebay_app.services.oauth import call
from logistics_app.models import Warehouse

NO_WAREHOUSE = "Es gibt noch keinen Lagerort. Bitte zuerst im Reiter „Lager“ anlegen."


def sync_default_location():
    """Transfer the default warehouse to eBay; an address change creates a new key."""
    warehouse = Warehouse.default()
    if warehouse is None:
        raise ValidationError(NO_WAREHOUSE)
    location = getattr(warehouse, "ebay_location", None)
    if location and not location.needs_resync:
        return location
    # eBay does not allow changing a location's address, so every transfer gets a fresh key.
    key = f"warehouse-{warehouse.pk}-{timezone.now():%Y%m%d%H%M%S}"
    call("POST", f"/sell/inventory/v1/location/{key}", json=_location_payload(warehouse))
    return _remember(warehouse, location, key)


def _location_payload(warehouse):
    """Build the createInventoryLocation body for a warehouse."""
    address = {
        "addressLine1": warehouse.street,
        "city": warehouse.city,
        "postalCode": warehouse.zip_code,
        "country": warehouse.country,
    }
    return {
        "location": {"address": address},
        "name": warehouse.name,
        "locationTypes": ["WAREHOUSE"],
        "merchantLocationStatus": "ENABLED",
    }


def _remember(warehouse, location, key):
    """Store (or replace) the eBay key of a warehouse."""
    location = location or EbayLocation(warehouse=warehouse)
    location.merchant_location_key = key
    location.last_synced = timezone.now()
    location.save()
    return location
