"""Shipping profiles: several eBay shipping policies the seller can choose from per listing."""

from decimal import Decimal

from django.db.models import Count
from rest_framework.exceptions import APIException, ValidationError

from ebay_app.models import EbayShippingProfile
from ebay_app.services.account import ensure_policy_opt_in, find_policy_id, policy_base
from ebay_app.services.oauth import call

POLICY_PATH = "/sell/account/v1/fulfillment_policy"
POLICY_PREFIX = "EricKun-Ya Versand – "  # eBay policy name = prefix + profile name
CURRENCY = "EUR"
NAME_MAX = 60  # length of EbayShippingProfile.name
IS_DEFAULT = "Das Standard-Profil kann nicht gelöscht werden. Bitte zuerst ein anderes als Standard festlegen."


def list_profiles():
    """Return all profiles with their listing count; missing details are read from eBay once."""
    for profile in EbayShippingProfile.objects.filter(shipping_service="").exclude(policy_id=""):
        _fill_from_ebay(profile)
    # Grouped queries ignore Meta.ordering, so the order is repeated here: default first, then by name.
    return EbayShippingProfile.objects.annotate(listing_count=Count("listings")).order_by("-is_default", "name")


def adopt(policy_id):
    """Return the profile that stands for an existing eBay shipping policy, creating it if needed."""
    if not policy_id:
        return None
    profile = EbayShippingProfile.objects.filter(policy_id=policy_id).first()
    if profile:
        return profile
    policy = call("GET", f"{POLICY_PATH}/{policy_id}")
    profile = EbayShippingProfile(name=_free_name(policy.get("name") or policy_id), policy_id=policy_id)
    _apply_policy(profile, policy)
    return profile


def _free_name(name):
    """Return the policy's name (without our own prefix) as profile name, numbered if it is taken."""
    name = name.removeprefix(POLICY_PREFIX)[:NAME_MAX]
    candidate, number = name, 2
    while EbayShippingProfile.objects.filter(name=candidate).exists():
        candidate = f"{name[:NAME_MAX - 5]} ({number})"
        number += 1
    return candidate


def _fill_from_ebay(profile):
    """Copy service, cost and handling time from eBay into a profile adopted by the migration."""
    try:
        policy = call("GET", f"{POLICY_PATH}/{profile.policy_id}")
    except APIException:
        return  # not connected or eBay unavailable: try again on the next load
    _apply_policy(profile, policy)


def _apply_policy(profile, policy):
    """Store the first domestic service, its cost and the handling time of an eBay policy."""
    option = (policy.get("shippingOptions") or [{}])[0]
    service = (option.get("shippingServices") or [{}])[0]
    profile.shipping_service = service.get("shippingServiceCode", "")
    profile.shipping_cost = Decimal((service.get("shippingCost") or {}).get("value", "0"))
    profile.handling_days = (policy.get("handlingTime") or {}).get("value", 1)
    profile.save()


def save_profile(profile, data):
    """Create or update the profile's shipping policy on eBay, then store the profile."""
    ensure_policy_opt_in()
    for field, value in data.items():
        setattr(profile, field, value)
    payload = _policy_payload(profile)
    profile.policy_id = profile.policy_id or find_policy_id("fulfillment", payload["name"])
    if profile.policy_id:
        call("PUT", f"{POLICY_PATH}/{profile.policy_id}", json=payload)
    else:
        profile.policy_id = call("POST", POLICY_PATH, json=payload)["fulfillmentPolicyId"]
    profile.save()
    return profile


def delete_profile(profile):
    """Delete an unused, non-default profile together with its policy on eBay."""
    if profile.is_default:
        raise ValidationError(IS_DEFAULT)
    count = profile.listings.count()
    if count:
        raise ValidationError(f"Dieses Versandprofil wird noch von {count} Inserat(en) verwendet.")
    if profile.policy_id:
        call("DELETE", f"{POLICY_PATH}/{profile.policy_id}")
    profile.delete()


def set_default(profile):
    """Make the profile the one used when a listing names no profile."""
    profile.is_default = True
    profile.save()
    return profile


def _policy_payload(profile):
    """Build a flat-rate domestic shipping policy from the profile."""
    cost = Decimal(profile.shipping_cost)
    service = {
        "shippingServiceCode": profile.shipping_service,
        "shippingCost": {"value": f"{cost:.2f}", "currency": CURRENCY},
        "freeShipping": cost == 0,
        "sortOrder": 1,
    }
    return {
        **policy_base(f"{POLICY_PREFIX}{profile.name}"),
        "handlingTime": {"unit": "DAY", "value": profile.handling_days},
        "shippingOptions": [{"optionType": "DOMESTIC", "costType": "FLAT_RATE", "shippingServices": [service]}],
    }
