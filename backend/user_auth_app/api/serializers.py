from django.contrib.auth.models import User
from rest_framework import serializers

from user_auth_app.models import UserProfile


class SimpleUserSerializer(serializers.ModelSerializer):
    """
    A simplified serializer for the User model.

    Displays basic, non-sensitive user information.
    Maps 'first_name' to 'fullname' for frontend convenience.
    """

    fullname = serializers.CharField(source="first_name")

    class Meta:
        model = User
        fields = ["id", "email", "fullname"]

    def update(self, instance, validated_data):
        """Set the username to the email upon update for consistency."""
        if "email" in validated_data:
            instance.username = validated_data["email"]
        return super().update(instance, validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for the UserProfile model with nested user data."""

    user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ["user", "bio", "location"]


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Handles validation for matching passwords and unique email addresses.
    """

    fullname = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    repeated_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["fullname", "email", "password", "repeated_password"]

    def validate(self, data):
        """Check that the two password fields match."""
        if data.get("password") != data.get("repeated_password"):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def validate_email(self, value):
        """Check if the email is already in use."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        """Create and return a new user instance."""
        fullname = validated_data.pop("fullname")
        validated_data.pop("repeated_password")

        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=fullname,
        )

        return user
