"""Translate the internal product condition into the eBay condition a category accepts."""

from rest_framework.exceptions import ValidationError

from products_app.models import Product

# eBay condition enum -> numeric condition id used by the category policies.
CONDITION_IDS = {
    "NEW": "1000",
    "LIKE_NEW": "2750",
    "USED_EXCELLENT": "3000",  # shown as plain "Gebraucht" in most categories
    "USED_VERY_GOOD": "4000",
    "USED_GOOD": "5000",
    "USED_ACCEPTABLE": "6000",
    "FOR_PARTS_OR_NOT_WORKING": "7000",
}
# Preferred eBay condition first; many categories only know the generic "used".
CANDIDATES = {
    Product.Condition.NEW: ["NEW"],
    Product.Condition.LIKE_NEW: ["LIKE_NEW", "USED_EXCELLENT"],
    Product.Condition.VERY_GOOD: ["USED_VERY_GOOD", "USED_EXCELLENT"],
    Product.Condition.GOOD: ["USED_GOOD", "USED_EXCELLENT"],
    Product.Condition.ACCEPTABLE: ["USED_ACCEPTABLE", "USED_EXCELLENT"],
    Product.Condition.FOR_PARTS: ["FOR_PARTS_OR_NOT_WORKING"],
}
NOT_ALLOWED = "Der Zustand „{label}“ ist in dieser eBay-Kategorie nicht erlaubt."
COARSER = "eBay kennt in dieser Kategorie nur „Gebraucht“. Dein Zustand „{label}“ steht zusätzlich als Notiz im Inserat."


def ebay_condition(product, allowed_ids):
    """Return the first eBay condition the category accepts for the product's condition."""
    for name in CANDIDATES[product.condition]:
        if not allowed_ids or CONDITION_IDS[name] in allowed_ids:
            return name
    raise ValidationError(NOT_ALLOWED.format(label=product.get_condition_display()))


def condition_hint(product, allowed_ids):
    """Return a note for the listing form if eBay shows a coarser condition or rejects it."""
    label = product.get_condition_display()
    preferred = CANDIDATES[product.condition][0]
    if not allowed_ids or CONDITION_IDS[preferred] in allowed_ids:
        return ""
    if any(CONDITION_IDS[name] in allowed_ids for name in CANDIDATES[product.condition]):
        return COARSER.format(label=label)
    return NOT_ALLOWED.format(label=label)


def condition_note(product, condition):
    """Return the note that keeps our finer grading visible on used items ("" for new ones)."""
    if condition == "NEW":
        return ""
    return f"Zustand: {product.get_condition_display()}"
