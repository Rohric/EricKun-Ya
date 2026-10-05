"""Low-level HTTP access to the eBay REST APIs of the configured environment."""

import base64

import requests
from django.conf import settings

from ebay_app.exceptions import EbayApiError, EbayNotConfigured

ENVIRONMENTS = {
    "sandbox": {
        "auth": "https://auth.sandbox.ebay.com/oauth2/authorize",
        "api": "https://api.sandbox.ebay.com",
        "media": "https://apim.sandbox.ebay.com",
        "web": "https://www.sandbox.ebay.de",
    },
    "production": {
        "auth": "https://auth.ebay.com/oauth2/authorize",
        "api": "https://api.ebay.com",
        "media": "https://apim.ebay.com",
        "web": "https://www.ebay.de",
    },
}
SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
]
REQUIRED_SETTINGS = ("EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET", "EBAY_RUNAME", "EBAY_TOKEN_KEY")
TIMEOUT_SECONDS = 20
LOCALE = "de-DE"  # language of listings and of the names eBay returns
MAX_ERRORS_SHOWN = 3


def environment():
    """Return the URL set of the configured eBay environment (sandbox by default)."""
    return ENVIRONMENTS.get(settings.EBAY_ENV, ENVIRONMENTS["sandbox"])


def missing_settings():
    """Return the names of required eBay settings that are empty."""
    return [name for name in REQUIRED_SETTINGS if not getattr(settings, name, "")]


def require_credentials():
    """Raise if any required eBay setting is missing."""
    missing = missing_settings()
    if missing:
        raise EbayNotConfigured(f"In der .env fehlt: {', '.join(missing)}")


def basic_auth_header():
    """Return the Basic auth header built from client id and secret."""
    raw = f"{settings.EBAY_CLIENT_ID}:{settings.EBAY_CLIENT_SECRET}".encode()
    return {"Authorization": f"Basic {base64.b64encode(raw).decode()}"}


def request(method, path, access_token=None, headers=None, host="api", **kwargs):
    """Send a request to an eBay host ("api" or "media") and return the parsed JSON body (or {})."""
    all_headers = {"Accept": "application/json", **(headers or {})}
    if access_token:
        all_headers["Authorization"] = f"Bearer {access_token}"
    response = _send(method, f"{environment()[host]}{path}", all_headers, kwargs)
    if response.status_code >= 400:
        raise EbayApiError(_error_message(response), http_status=response.status_code)
    return _json_or_empty(response)


def _send(method, url, headers, kwargs):
    """Perform the HTTP call; network failures become an EbayApiError."""
    try:
        return requests.request(method, url, headers=headers, timeout=TIMEOUT_SECONDS, **kwargs)
    except requests.RequestException as exc:
        raise EbayApiError(f"eBay ist nicht erreichbar ({exc.__class__.__name__}).") from exc


def _json_or_empty(response):
    """Return the JSON body, or {} for empty and non-JSON success responses."""
    try:
        return response.json() if response.content else {}
    except ValueError:
        return {}


def _error_message(response):
    """Extract the most helpful message(s) from an eBay error response."""
    try:
        data = response.json()
    except ValueError:
        return f"eBay-Fehler {response.status_code}."
    errors = data.get("errors") or []
    if errors:
        return " · ".join(_error_text(error) for error in errors[:MAX_ERRORS_SHOWN])
    return data.get("error_description") or data.get("error") or f"eBay-Fehler {response.status_code}."


def _error_text(error):
    """Return the readable text of a single eBay error entry."""
    return error.get("longMessage") or error.get("message") or str(error)
