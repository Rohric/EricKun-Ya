"""Authentication endpoints: registration (login/refresh/logout via simplejwt)."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegistrationSerializer


class RegistrationView(APIView):
    """Register a new user and return a JWT token pair."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Create the user and issue access and refresh tokens."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_token_payload(user), status=status.HTTP_201_CREATED)


def _token_payload(user):
    """Return a fresh JWT pair together with the user's email and id."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "email": user.email,
        "user_id": user.id,
    }
