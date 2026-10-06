"""Translate between the internal product condition and the eBay condition of a listing."""

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
# eBay condition -> our condition when a listing is taken over from eBay (default: good).
FROM_EBAY = {
    "NEW": Product.Condition.NEW,
    "NEW_OTHER": Product.Condition.LIKE_NEW,
    "NEW_WITH_DEFECTS": Product.Condition.LIKE_NEW,
    "LIKE_NEW": Product.Condition.LIKE_NEW,
    "USED_VERY_GOOD": Product.Condition.VERY_GOOD,
    "USED_ACCEPTABLE": Product.Condition.ACCEPTABLE,
    "FOR_PARTS_OR_NOT_WORKING": Product.Condition.FOR_PARTS,
}
NOTE_PREFIX = "Zustand: "


def ebay_condition(product, allowed_ids):
    """Return the first eBay condition the category accepts for the product's condition."""
    for name in CANDIDATES[product.condition]:
        if not allowed_ids or CONDITION_IDS[name] in allowed_ids:
            return name
    raise ValidationError(_not_allowed(product))


def condition_hint(product, allowed_ids):
    """Return a note for the listing form if eBay shows a coarser condition or rejects it."""
    preferred = CANDIDATES[product.condition][0]
    if not allowed_ids or CONDITION_IDS[preferred] in allowed_ids:
        return ""
    if any(CONDITION_IDS[name] in allowed_ids for name in CANDIDATES[product.condition]):
        label = product.get_condition_display()
        return f"eBay kennt in dieser Kategorie nur „Gebraucht“. Dein Zustand „{label}“ steht zusätzlich als Notiz im Inserat."
    return _not_allowed(product)


def condition_note(product, condition):
    """Return the note that keeps our finer grading visible on used items ("" for new ones)."""
    if condition == "NEW":
        return ""
    return f"{NOTE_PREFIX}{product.get_condition_display()}"


def product_condition(condition, note=""):
    """Return our condition for a listing taken over from eBay; our own note on it wins."""
    return _condition_from_note(note) or FROM_EBAY.get(condition, Product.Condition.GOOD)


def _condition_from_note(note):
    """Read back the grading we once wrote into a listing ("Zustand: Sehr gut"), or None."""
    if not (note or "").startswith(NOTE_PREFIX):
        return None
    labels = {str(label): value for value, label in Product.Condition.choices}
    return labels.get(note.removeprefix(NOTE_PREFIX).strip())


def _not_allowed(product):
    """Return the message for a condition the eBay category does not accept."""
    return f"Der Zustand „{product.get_condition_display()}“ ist in dieser eBay-Kategorie nicht erlaubt."
