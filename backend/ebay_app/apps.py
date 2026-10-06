"""App configuration of the eBay app."""

from django.apps import AppConfig


class EbayAppConfig(AppConfig):
    """Configure the eBay app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ebay_app"

    def ready(self):
        """Register signal handlers."""
        from ebay_app import signals  # noqa: F401
