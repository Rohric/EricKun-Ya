"""Project-wide DRF exception handling."""

from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Wrap DRF error responses in a consistent {"error": ...} envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    response.data = {"error": response.data}
    return response
