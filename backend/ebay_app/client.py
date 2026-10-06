"""Low-level HTTP access to eBay: the REST APIs and the older XML Trading API."""

import base64
from xml.etree import ElementTree

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
# Trading API (XML): the only way to reach listings that were created outside the Inventory API.
TRADING_PATH = "/ws/api.dll"
TRADING_NAMESPACE = "urn:ebay:apis:eBLBaseComponents"
TRADING_VERSION = "1193"
SITE_IDS = {"EBAY_DE": "77", "EBAY_AT": "16", "EBAY_CH": "193"}  # Trading API ids of the marketplaces
DEFAULT_SITE_ID = "77"
DOWNLOAD_FAILED = "Die Datei konnte nicht von eBay geladen werden."


def environment():
    """Return the URL set of the configured eBay environment (sandbox by default)."""
    return ENVIRONMENTS.get(settings.EBAY_ENV, ENVIRONMENTS["sandbox"])


def missing_settings():
    """Return the names of required eBay settings that are empty."""
    return [name for name in REQUIRED_SETTINGS if not getattr(settings, name, "")]


def require_credentials():
    """Raise if any required eBay setting is missing."""
    missing = ", ".join(missing_settings())
    if missing:
        raise EbayNotConfigured(f"In der .env fehlt: {missing}")


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


def download(url):
    """Fetch a public file (e.g. a listing image) and return its bytes."""
    response = _send("GET", url, {}, {})
    if response.status_code >= 400:
        raise EbayApiError(DOWNLOAD_FAILED, http_status=response.status_code)
    return response.content


# --- Trading API (XML) ---

def trading_request(call_name, body, access_token):
    """Call the Trading API with nested dicts as body and return the response as nested dicts."""
    host, headers = environment()["api"], _trading_headers(call_name, access_token)
    response = _send("POST", f"{host}{TRADING_PATH}", headers, {"data": _to_xml(call_name, body)})
    data = _from_xml(response.content)
    if response.status_code >= 400 or data.get("Ack") == "Failure":
        raise EbayApiError(_trading_error(data, response.status_code), http_status=response.status_code)
    return data


def _trading_headers(call_name, access_token):
    """Return the headers that name the call, the marketplace and the seller's OAuth token."""
    return {
        "X-EBAY-API-CALL-NAME": call_name,
        "X-EBAY-API-SITEID": SITE_IDS.get(settings.EBAY_MARKETPLACE_ID, DEFAULT_SITE_ID),
        "X-EBAY-API-COMPATIBILITY-LEVEL": TRADING_VERSION,
        "X-EBAY-API-IAF-TOKEN": access_token,
        "Content-Type": "text/xml",
    }


def _to_xml(call_name, body):
    """Serialize nested dicts into the request document of a call (a list repeats its tag)."""
    root = ElementTree.Element(f"{call_name}Request", xmlns=TRADING_NAMESPACE)
    _append(root, body)
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _append(parent, body):
    """Add a dict's entries as child elements; nested dicts and lists recurse."""
    for name, value in body.items():
        for entry in value if isinstance(value, list) else [value]:
            child = ElementTree.SubElement(parent, name)
            if isinstance(entry, dict):
                _append(child, entry)
            else:
                child.text = str(entry)


def _from_xml(content):
    """Parse a response document into nested dicts ({} if it is not XML)."""
    try:
        return _node(ElementTree.fromstring(content))
    except ElementTree.ParseError:
        return {}


def _node(element):
    """Return an element's text, or a dict of its children (a repeated tag becomes a list)."""
    if not len(element):
        return (element.text or "").strip()
    data = {}
    for child in element:
        name, value = child.tag.split("}")[-1], _node(child)
        data[name] = [*as_list(data[name]), value] if name in data else value
    return data


def as_list(value):
    """Return a parsed XML value as list, because a tag that occurs once is not a list."""
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def _trading_error(data, status_code):
    """Extract the readable messages of a failed Trading API call."""
    errors = as_list(data.get("Errors"))[:MAX_ERRORS_SHOWN]
    texts = [error.get("LongMessage") or error.get("ShortMessage", "") for error in errors]
    return " · ".join(filter(None, texts)) or f"eBay-Fehler {status_code}."
