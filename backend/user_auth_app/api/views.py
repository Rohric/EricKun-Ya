from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from user_auth_app.models import UserProfile

from .serializers import (
    RegistrationSerializer,
    SimpleUserSerializer,
    UserProfileSerializer,
)


class UserProfileList(generics.ListCreateAPIView):
    """API endpoint to list or create user profiles."""

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

    def get(self, request):
        """Handle GET request to list user profiles."""
        return super().get(request)


class UserListView(APIView):
    """API endpoint to list all users with basic information."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return a list of all users (id, email, username)."""
        users = User.objects.all().values("id", "email", "username")
        return Response(list(users))


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API endpoint to retrieve, update, or delete a single user."""

    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = SimpleUserSerializer


class UserProfileDetail(generics.RetrieveUpdateDestroyAPIView):
    """API endpoint to retrieve, update, or delete a single user profile."""

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class RegistrationView(APIView):
    """API endpoint for user registration."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Handle user registration and return an auth token on success."""
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "token": token.key,
                    "fullname": user.first_name,
                    "email": user.email,
                    "user_id": user.id,
                },
                status=201,
            )

        return Response(serializer.errors, status=400)


class LoginView(APIView):
    """API endpoint for user login."""

    permission_classes = []

    def post(self, request):
        """Handle user authentication and return an auth token on success."""
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=email, password=password)

        if not user:
            return Response({"error": "Invalid credentials"}, status=400)

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "fullname": user.first_name,
                "email": user.email,
                "user_id": user.id,
            },
            status=200,
        )


class LogoutView(APIView):
    """API endpoint for user logout."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Delete the user's authentication token from the server."""
        token = getattr(request.user, "auth_token", None)

        if token:
            token.delete()

        return Response(
            {"detail": "Logout erfolgreich. Token wurde gelöscht."},
            status=status.HTTP_200_OK,
        )


class EmailCheckView(APIView):
    """API endpoint to check if an email address is already registered."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Check for the existence of a user by email.

        The email is passed as a query parameter.

        Returns:
            - 200 with user data if found.
            - 400 if the email parameter is missing.
            - 404 if the email is not found.
            - 500 for any other server error.
        """
        email = request.query_params.get("email", None)

        if not email:
            return Response(status=400)

        try:
            user = User.objects.get(email=email)
            serializer = SimpleUserSerializer(user)
            return Response(serializer.data, status=200)
        except User.DoesNotExist:
            return Response(status=404)
        except Exception:
            return Response(status=500)
