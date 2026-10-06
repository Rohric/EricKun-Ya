"""App configuration of the auth app."""

from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    """Configure the auth app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "auth_app"
