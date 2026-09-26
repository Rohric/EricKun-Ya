from django.apps import AppConfig


class FinanceAppConfig(AppConfig):
    """Configure the finance app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "finance_app"
