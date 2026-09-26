from django.apps import AppConfig


class ProductsAppConfig(AppConfig):
    """Configure the products app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "products_app"

    def ready(self):
        """Register signal handlers."""
        from products_app import signals  # noqa: F401
