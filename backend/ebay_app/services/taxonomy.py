"""eBay category data: suggestions for a title, aspects to fill in and allowed conditions."""

from django.conf import settings
from django.core.cache import cache

from ebay_app import client
from ebay_app.services.oauth import call

TAXONOMY = "/commerce/taxonomy/v1"
CACHE_SECONDS = 24 * 60 * 60  # category rules change rarely
LANGUAGE = {"Accept-Language": client.LOCALE}


def _cache_key(kind, suffix=""):
    """Return a cache key that is unique per environment and marketplace."""
    return f"ebay-{kind}-{settings.EBAY_ENV}-{settings.EBAY_MARKETPLACE_ID}-{suffix}"


def _tree_id():
    """Return the id of the marketplace's default category tree (cached)."""
    return cache.get_or_set(_cache_key("tree"), _fetch_tree_id, CACHE_SECONDS)


def _fetch_tree_id():
    """Ask eBay for the default category tree of the marketplace."""
    params = {"marketplace_id": settings.EBAY_MARKETPLACE_ID}
    return call("GET", f"{TAXONOMY}/get_default_category_tree_id", params=params)["categoryTreeId"]


def suggest_categories(query):
    """Return eBay's category suggestions (id, name, path) for a product title."""
    path = f"{TAXONOMY}/category_tree/{_tree_id()}/get_category_suggestions"
    data = call("GET", path, headers=LANGUAGE, params={"q": query})
    return [_suggestion(item) for item in data.get("categorySuggestions", [])]


def _suggestion(item):
    """Map a suggestion to {id, name, path}; eBay lists the ancestors leaf-first."""
    category = item["category"]
    ancestors = [node["categoryName"] for node in reversed(item.get("categoryTreeNodeAncestors", []))]
    return {
        "id": category["categoryId"],
        "name": category["categoryName"],
        "path": " › ".join([*ancestors, category["categoryName"]]),
    }


def category_requirements(category_id):
    """Return the aspects to fill in and the condition ids eBay accepts in a category."""
    return {
        "aspects": category_aspects(category_id),
        "condition_ids": sorted(allowed_condition_ids(category_id)),
    }


def category_aspects(category_id):
    """Return the required and recommended aspects of a category (cached)."""
    key = _cache_key("aspects", category_id)
    return cache.get_or_set(key, lambda: _fetch_aspects(category_id), CACHE_SECONDS)


def _fetch_aspects(category_id):
    """Load a category's aspects from eBay and drop the purely optional ones."""
    path = f"{TAXONOMY}/category_tree/{_tree_id()}/get_item_aspects_for_category"
    data = call("GET", path, headers=LANGUAGE, params={"category_id": category_id})
    aspects = [_aspect(raw) for raw in data.get("aspects", [])]
    return [aspect for aspect in aspects if aspect["required"] or aspect["recommended"]]


def _aspect(raw):
    """Map an eBay aspect to the fields the listing form needs."""
    constraint = raw.get("aspectConstraint", {})
    return {
        "name": raw["localizedAspectName"],
        "required": bool(constraint.get("aspectRequired")),
        "recommended": constraint.get("aspectUsage") == "RECOMMENDED",
        "multiple": constraint.get("itemToAspectCardinality") == "MULTI",
        "free_text": constraint.get("aspectMode") != "SELECTION_ONLY",
        "values": [value["localizedValue"] for value in raw.get("aspectValues", [])],
    }


def allowed_condition_ids(category_id):
    """Return the condition ids eBay accepts in a category (cached; empty = unknown)."""
    key = _cache_key("conditions", category_id)
    return cache.get_or_set(key, lambda: _fetch_condition_ids(category_id), CACHE_SECONDS)


def _fetch_condition_ids(category_id):
    """Load a category's item condition policy from eBay."""
    path = f"/sell/metadata/v1/marketplace/{settings.EBAY_MARKETPLACE_ID}/get_item_condition_policies"
    data = call("GET", path, params={"filter": f"categoryIds:{{{category_id}}}"})
    policies = data.get("itemConditionPolicies") or [{}]
    return {condition["conditionId"] for condition in policies[0].get("itemConditions", [])}
