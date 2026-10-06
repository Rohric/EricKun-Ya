"""OAuth 2.0 authorization code flow against eBay: connect, token storage and refresh."""

import secrets
from datetime import timedelta
from urllib.parse import parse_qs, quote, urlencode, urlparse

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ebay_app import client, crypto
from ebay_app.exceptions import EbayNotConnected
from ebay_app.models import EbayAccount

TOKEN_PATH = "/identity/v1/oauth2/token"
STATE_LIFETIME = timedelta(minutes=10)
REFRESH_MARGIN = timedelta(seconds=60)
APP_TOKEN_MARGIN = 300  # seconds an application token is dropped from the cache before it expires
NO_CODE = "In der Adresse steht kein eBay-Code. Bitte die komplette Adresse aus der Browserleiste einfügen."
BAD_STATE = "Die Anmeldung ist abgelaufen oder passt nicht. Bitte erneut „Mit eBay verbinden“ klicken."


def start_connection():
    """Create a fresh CSRF state and return the eBay consent URL."""
    client.require_credentials()
    account = EbayAccount.load()
    account.oauth_state = secrets.token_urlsafe(24)
    account.oauth_state_created_at = timezone.now()
    account.save(update_fields=["oauth_state", "oauth_state_created_at"])
    return _consent_url(account.oauth_state)


def _consent_url(state):
    """Build eBay's consent URL for our application, scopes and the given CSRF state."""
    params = {
        "client_id": settings.EBAY_CLIENT_ID,
        "redirect_uri": settings.EBAY_RUNAME,
        "response_type": "code",
        "scope": " ".join(client.SCOPES),
        "state": state,
    }
    auth_url = client.environment()["auth"]
    return f"{auth_url}?{urlencode(params, quote_via=quote)}"


def finish_connection(redirect_url):
    """Check the pasted redirect URL, exchange its code for tokens and store them."""
    client.require_credentials()
    account = EbayAccount.load()
    code = _code_from_redirect(redirect_url, account)
    tokens = _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.EBAY_RUNAME,
    })
    _store_tokens(account, tokens)
    account.oauth_state = ""
    account.connected_at = timezone.now()
    account.save()


def _token_request(data):
    """Call the eBay token endpoint with Basic auth."""
    return client.request("POST", TOKEN_PATH, headers=client.basic_auth_header(), data=data)


def _code_from_redirect(redirect_url, account):
    """Return the authorization code after checking the CSRF state and its age."""
    query = parse_qs(urlparse(redirect_url.strip()).query)
    code = query.get("code", [""])[0]
    state = query.get("state", [account.oauth_state])[0]  # tolerate landing pages that drop the state
    if not code:
        raise ValidationError(NO_CODE)
    if _state_expired(account) or state != account.oauth_state:
        raise ValidationError(BAD_STATE)
    return code


def _state_expired(account):
    """Return True if no connection was started or it is older than STATE_LIFETIME."""
    created = account.oauth_state_created_at
    return not account.oauth_state or created is None or timezone.now() - created > STATE_LIFETIME


def _store_tokens(account, tokens):
    """Encrypt and store a token response (the refresh token only if one was returned)."""
    now = timezone.now()
    account.access_token = crypto.encrypt(tokens["access_token"])
    account.access_expires_at = now + timedelta(seconds=tokens.get("expires_in", 7200))
    if tokens.get("refresh_token"):
        account.refresh_token = crypto.encrypt(tokens["refresh_token"])
        account.refresh_expires_at = now + timedelta(seconds=tokens.get("refresh_token_expires_in", 0))


def get_access_token():
    """Return a valid access token, refreshing it shortly before it expires."""
    account = EbayAccount.load()
    if not account.is_connected:
        raise EbayNotConnected()
    expires = account.access_expires_at
    if expires and expires - REFRESH_MARGIN > timezone.now():
        return crypto.decrypt(account.access_token)
    return _refresh(account)


def _refresh(account):
    """Mint a new access token with the stored refresh token."""
    client.require_credentials()
    tokens = _token_request({
        "grant_type": "refresh_token",
        "refresh_token": crypto.decrypt(account.refresh_token),
        "scope": " ".join(client.SCOPES),
    })
    _store_tokens(account, tokens)
    account.save(update_fields=["access_token", "access_expires_at", "refresh_token", "refresh_expires_at"])
    return tokens["access_token"]


def call(method, path, **kwargs):
    """Call the eBay API on behalf of the connected seller."""
    return client.request(method, path, access_token=get_access_token(), **kwargs)


def trading_call(call_name, body):
    """Call eBay's older Trading API (XML) on behalf of the connected seller."""
    return client.trading_request(call_name, body, get_access_token())


def get_app_token():
    """Return an application token for public data (e.g. the buyer's view), cached until it expires."""
    key = f"ebay-app-token-{settings.EBAY_ENV}"
    token = cache.get(key)
    if token:
        return token
    client.require_credentials()
    tokens = _token_request({"grant_type": "client_credentials", "scope": client.SCOPES[0]})
    cache.set(key, tokens["access_token"], max(tokens.get("expires_in", 7200) - APP_TOKEN_MARGIN, 60))
    return tokens["access_token"]


def disconnect():
    """Forget the stored tokens (eBay has no revoke call; the grant simply lapses)."""
    account = EbayAccount.load()
    account.access_token = account.refresh_token = ""
    account.access_expires_at = account.refresh_expires_at = account.connected_at = None
    account.save()
