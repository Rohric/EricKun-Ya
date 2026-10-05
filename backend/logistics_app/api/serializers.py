"""Serializers for the logistics app."""

from rest_framework import serializers

from logistics_app.models import Warehouse

COUNTRY_ERROR = "Bitte einen 2-stelligen Ländercode angeben (z. B. DE)."


class WarehouseSerializer(serializers.ModelSerializer):
    """Serialize a warehouse (storage location / ship-from address)."""

    class Meta:
        model = Warehouse
        fields = ["id", "name", "street", "zip_code", "city", "country", "is_default", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"country": {"error_messages": {"max_length": COUNTRY_ERROR}}}

    def validate_country(self, value):
        """Normalise the ISO country code (e.g. 'de' -> 'DE')."""
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError(COUNTRY_ERROR)
        return value
