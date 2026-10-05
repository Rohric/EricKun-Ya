"""Seller setup on eBay: business policy opt-in, the three policies and shipping services."""

from decimal import Decimal

from django.conf import settings

from ebay_app.models import EbayAccount
from ebay_app.services.oauth import call

POLICY_PROGRAM = "SELLING_POLICY_MANAGEMENT"
POLICY_KINDS = ("fulfillment", "return", "payment")
POLICY_NAMES = {
    "fulfillment": "EricKun-Ya Versand",
    "return": "EricKun-Ya Rückgabe",
    "payment": "EricKun-Ya Zahlung",
}
CATEGORY_TYPES = [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}]
CURRENCY = "EUR"
DEFAULT_FORM = {
    "shipping_service": "",
    "shipping_cost": "",
    "handling_days": 1,
    "return_days": 30,
    "return_cost_payer": "BUYER",
}


def ensure_policy_opt_in():
    """Opt the seller into business policies unless that is already done."""
    programs = call("GET", "/sell/account/v1/program/get_opted_in_programs").get("programs", [])
    if any(program.get("programType") == POLICY_PROGRAM for program in programs):
        return
    call("POST", "/sell/account/v1/program/opt_in", json={"programType": POLICY_PROGRAM})


def shipping_services():
    """Return the marketplace's domestic, still valid shipping services as code/name pairs."""
    path = f"/sell/metadata/v1/shipping/marketplace/{settings.EBAY_MARKETPLACE_ID}/get_shipping_services"
    data = call("GET", path, headers={"Accept-Language": "de-DE"})
    return _unique_by_code(_service_option(s) for s in data.get("shippingServices", []) if _is_domestic(s))


def _unique_by_code(options):
    """Drop repeated codes: eBay lists one entry per package size, the first has the general name."""
    unique = {}
    for option in options:
        unique.setdefault(option["code"], option)
    return list(unique.values())


def _is_domestic(service):
    """Return True for domestic services that may still be offered."""
    return not service.get("internationalService") and service.get("validForSellingFlow", True)


def _service_option(service):
    """Map an eBay shipping service to {code, name} (the code field name varies between APIs)."""
    code = service.get("shippingServiceCode") or service.get("shippingService", "")
    return {"code": code, "name": service.get("description") or code}


def save_policies(form):
    """Opt in if needed, then create or update all three policies and store their ids."""
    ensure_policy_opt_in()
    account = EbayAccount.load()
    builders = {"fulfillment": _fulfillment_payload, "return": _return_payload, "payment": _payment_payload}
    for kind in POLICY_KINDS:
        _upsert_policy(account, kind, builders[kind](form))
    account.save()


def _upsert_policy(account, kind, payload):
    """Update the known policy, or create it (re-using an existing one with our name)."""
    path = f"/sell/account/v1/{kind}_policy"
    policy_id = getattr(account, f"{kind}_policy_id") or _find_policy_id(kind)
    if policy_id:
        call("PUT", f"{path}/{policy_id}", json=payload)
    else:
        policy_id = call("POST", path, json=payload)[f"{kind}PolicyId"]
    setattr(account, f"{kind}_policy_id", policy_id)


def _find_policy_id(kind):
    """Return the id of an existing policy with our name, e.g. after a database reset."""
    params = {"marketplace_id": settings.EBAY_MARKETPLACE_ID}
    for policy in call("GET", f"/sell/account/v1/{kind}_policy", params=params).get(f"{kind}Policies", []):
        if policy.get("name") == POLICY_NAMES[kind]:
            return policy[f"{kind}PolicyId"]
    return ""


def _base(kind):
    """Return the fields every policy shares."""
    return {"name": POLICY_NAMES[kind], "marketplaceId": settings.EBAY_MARKETPLACE_ID, "categoryTypes": CATEGORY_TYPES}


def _fulfillment_payload(form):
    """Build a flat-rate domestic shipping policy from the form."""
    cost = Decimal(form["shipping_cost"])
    service = {
        "shippingServiceCode": form["shipping_service"],
        "shippingCost": {"value": f"{cost:.2f}", "currency": CURRENCY},
        "freeShipping": cost == 0,
        "sortOrder": 1,
    }
    return {
        **_base("fulfillment"),
        "handlingTime": {"unit": "DAY", "value": form["handling_days"]},
        "shippingOptions": [{"optionType": "DOMESTIC", "costType": "FLAT_RATE", "shippingServices": [service]}],
    }


def _return_payload(form):
    """Build the return policy (returns accepted, money back)."""
    return {
        **_base("return"),
        "returnsAccepted": True,
        "returnPeriod": {"unit": "DAY", "value": form["return_days"]},
        "returnShippingCostPayer": form["return_cost_payer"],
        "refundMethod": "MONEY_BACK",
    }


def _payment_payload(form):
    """Build the payment policy (payments managed by eBay, immediate payment)."""
    return {**_base("payment"), "immediatePay": True}


def current_policies():
    """Return the stored policies' values for pre-filling the setup form."""
    account = EbayAccount.load()
    values = dict(DEFAULT_FORM)
    if account.fulfillment_policy_id:
        path = f"/sell/account/v1/fulfillment_policy/{account.fulfillment_policy_id}"
        values.update(_read_fulfillment(call("GET", path)))
    if account.return_policy_id:
        values.update(_read_return(call("GET", f"/sell/account/v1/return_policy/{account.return_policy_id}")))
    return values


def _read_fulfillment(policy):
    """Extract service, cost and handling time from a fulfillment policy."""
    option = (policy.get("shippingOptions") or [{}])[0]
    service = (option.get("shippingServices") or [{}])[0]
    return {
        "shipping_service": service.get("shippingServiceCode", ""),
        "shipping_cost": (service.get("shippingCost") or {}).get("value", ""),
        "handling_days": (policy.get("handlingTime") or {}).get("value", 1),
    }


def _read_return(policy):
    """Extract return period and cost payer from a return policy."""
    return {
        "return_days": (policy.get("returnPeriod") or {}).get("value", 30),
        "return_cost_payer": policy.get("returnShippingCostPayer", "BUYER"),
    }
