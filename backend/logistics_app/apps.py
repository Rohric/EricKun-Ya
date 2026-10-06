"""App configuration of the logistics app."""

from django.apps import AppConfig


class LogisticsAppConfig(AppConfig):
    """Configure the logistics app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "logistics_app"
