"""Serializers for user registration."""

from rest_framework import serializers

from auth_app.models import User


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate registration input and create a new user."""

    fullname = serializers.CharField(write_only=True)
    repeated_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "fullname", "password", "repeated_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        """Check that both password entries match."""
        if data["password"] != data["repeated_password"]:
            raise serializers.ValidationError("Die Passwörter stimmen nicht überein.")
        return data

    def create(self, validated_data):
        """Create a user, storing the full name in first_name."""
        validated_data.pop("repeated_password")
        fullname = validated_data.pop("fullname")
        return User.objects.create_user(first_name=fullname, **validated_data)
