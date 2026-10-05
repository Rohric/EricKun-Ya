"""Symmetric encryption of the stored eBay tokens (Fernet, key from EBAY_TOKEN_KEY)."""

from cryptography.fernet import Fernet
from django.conf import settings

from ebay_app.exceptions import EbayNotConfigured


def _fernet():
    """Return the Fernet cipher for the configured key."""
    if not settings.EBAY_TOKEN_KEY:
        raise EbayNotConfigured("In der .env fehlt: EBAY_TOKEN_KEY")
    return Fernet(settings.EBAY_TOKEN_KEY.encode())


def encrypt(value):
    """Return the encrypted form of a token (an empty value stays empty)."""
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt(value):
    """Return the plain token from its encrypted form (an empty value stays empty)."""
    return _fernet().decrypt(value.encode()).decode() if value else ""
