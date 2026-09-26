"""Serializers for the finance app."""

from rest_framework import serializers

from finance_app.models import FinanceSettings, Goal
from finance_app.services import goal_progress

DATE_ERRORS = {"invalid": "Ungültiges Datum (Format JJJJ-MM-TT)."}


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


class ReportRangeSerializer(serializers.Serializer):
    """Validate the optional ?from=&to= query parameters of the reports."""

    def get_fields(self):
        """Declare the fields here because 'from' is a Python keyword."""
        return {
            "from": serializers.DateField(required=False, error_messages=DATE_ERRORS),
            "to": serializers.DateField(required=False, error_messages=DATE_ERRORS),
        }

    def validate(self, data):
        """Reject a reversed range."""
        if data.get("from") and data.get("to") and data["from"] > data["to"]:
            raise serializers.ValidationError("„von“ darf nicht nach „bis“ liegen.")
        return data


class ReportYearSerializer(serializers.Serializer):
    """Validate the optional ?year= query parameter."""

    year = serializers.IntegerField(
        required=False,
        min_value=2000,
        max_value=2100,
        error_messages={"invalid": "Ungültiges Jahr."},
    )
