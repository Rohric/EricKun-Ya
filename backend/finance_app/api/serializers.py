"""Serializers for the finance app."""

from rest_framework import serializers

from finance_app.models import FinanceSettings, Goal
from finance_app.services import goal_progress


class GoalSerializer(serializers.ModelSerializer):
    """Serialize a goal and expose its computed progress read-only."""

    progress = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            "id", "title", "target_amount", "metric", "period",
            "start_date", "end_date", "is_active", "progress",
        ]

    def get_progress(self, obj):
        """Return the aggregated progress for the goal."""
        return goal_progress(obj)


class FinanceSettingsSerializer(serializers.ModelSerializer):
    """Serialize the adjustable finance settings."""

    class Meta:
        model = FinanceSettings
        fields = ["tax_reserve_rate"]
