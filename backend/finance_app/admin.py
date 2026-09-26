"""Admin configuration for the finance app."""

from django.contrib import admin

from finance_app.models import FinanceSettings, Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """Configure the goal list and detail view in the admin."""

    list_display = ("title", "metric", "period", "target_amount", "start_date", "end_date", "is_active")
    list_filter = ("metric", "period", "is_active")


@admin.register(FinanceSettings)
class FinanceSettingsAdmin(admin.ModelAdmin):
    """Configure the singleton finance settings in the admin."""

    list_display = ("tax_reserve_rate",)
