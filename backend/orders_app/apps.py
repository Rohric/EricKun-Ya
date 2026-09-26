from django.apps import AppConfig


class OrdersAppConfig(AppConfig):
    """Configure the orders app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "orders_app"
