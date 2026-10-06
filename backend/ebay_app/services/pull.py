"""Pull the seller's listings from eBay into our listing rows; nothing is changed on eBay."""

from ebay_app.models import EbayListing
from ebay_app.services import assignment, legacy
from ebay_app.services.listings import INVENTORY, remote_offer
from ebay_app.services.oauth import call
from ebay_app.services.snapshots import PUBLISHED, apply_snapshot, inventory_snapshot

PAGE_SIZE = 100  # eBay's maximum per page


def pull_listings():
    """Mirror eBay's listings, link those that carry one of our numbers and count the result."""
    found = _pull_inventory() + _pull_legacy()
    linked = assignment.link_exact_matches()
    return {"found": found, "linked": linked, "unassigned": assignment.unassigned().count()}


def _pull_inventory():
    """Mirror the listings managed through the Inventory API; return how many are online."""
    return sum(_store(item, remote_offer(item["sku"])) for item in _inventory_items())


def _inventory_items():
    """Yield every inventory item of the seller, page by page."""
    params = {"limit": PAGE_SIZE, "offset": 0}
    while True:
        page = call("GET", f"{INVENTORY}/inventory_item", params=params)
        yield from page.get("inventoryItems", [])
        params["offset"] += PAGE_SIZE
        if params["offset"] >= page.get("total", 0):
            return


def _store(item, offer):
    """Create or refresh the row of one inventory item; return 1 if it is online on eBay."""
    listing = EbayListing.objects.filter(sku=item["sku"], needs_migration=False).first()
    online = bool(offer) and offer.get("status") == PUBLISHED
    if listing is None and not online:
        return 0  # an item that is not online is not a listing
    if not online and listing.product_id is None:
        listing.delete()  # it left eBay before it was assigned to an article
        return 0
    apply_snapshot(listing or EbayListing(), inventory_snapshot(item, offer))
    return int(online)


def _pull_legacy():
    """Mirror the online listings that live outside the Inventory API; return how many there are."""
    converted = EbayListing.objects.filter(needs_migration=False).exclude(listing_id="")
    known = set(converted.values_list("listing_id", flat=True))
    snapshots = [snapshot for snapshot in legacy.active_listings() if snapshot["listing_id"] not in known]
    for snapshot in snapshots:
        row = EbayListing.objects.filter(listing_id=snapshot["listing_id"]).first() or EbayListing()
        apply_snapshot(row, {**snapshot, "needs_migration": True, "online": True})
    _drop_ended_legacy({snapshot["listing_id"] for snapshot in snapshots})
    return len(snapshots)


def _drop_ended_legacy(active_ids):
    """Forget legacy listings that are no longer online on eBay."""
    EbayListing.objects.filter(needs_migration=True).exclude(listing_id__in=active_ids).delete()
