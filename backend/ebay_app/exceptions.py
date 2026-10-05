"""eBay-specific API errors; rendered by the central DRF exception handler."""

from rest_framework import status
from rest_framework.exceptions import APIException


class EbayApiError(APIException):
    """eBay rejected a request or could not be reached."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "eBay hat die Anfrage abgelehnt."
    default_code = "ebay_error"

    def __init__(self, detail=None, code=None, http_status=None):
        """Keep eBay's own HTTP status so services can react to e.g. a 404."""
        super().__init__(detail, code)
        self.http_status = http_status


class EbayNotConnected(APIException):
    """No valid eBay connection exists (never connected or refresh token expired)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Nicht mit eBay verbunden. Bitte im eBay-Reiter verbinden."
    default_code = "ebay_not_connected"


class EbayNotConfigured(APIException):
    """Required eBay settings are missing in the .env."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "eBay ist noch nicht eingerichtet (Werte in der .env fehlen)."
    default_code = "ebay_not_configured"
