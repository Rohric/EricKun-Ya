"""API views for the eBay connection and the seller setup."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ebay_app.services import account, locations, oauth, overview

from .serializers import ConnectFinishSerializer, PolicyFormSerializer


class EbayStatusView(APIView):
    """Return the connection, setup and readiness state."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the status overview for the eBay tab."""
        return Response(overview.connection_status())


class ConnectStartView(APIView):
    """Start the OAuth flow."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Return the eBay consent URL for a fresh login."""
        return Response({"consent_url": oauth.start_connection()})


class ConnectFinishView(APIView):
    """Finish the OAuth flow with the redirect URL pasted after the eBay login."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Exchange the code from the pasted URL and store the tokens."""
        serializer = ConnectFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        oauth.finish_connection(serializer.validated_data["redirect_url"])
        return Response(overview.connection_status())


class DisconnectView(APIView):
    """Remove the stored eBay tokens."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Disconnect from eBay and return the new status."""
        oauth.disconnect()
        return Response(overview.connection_status())


class ShippingServicesView(APIView):
    """List the domestic shipping services eBay offers on the marketplace."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return code/name pairs for the shipping service dropdown."""
        return Response(account.shipping_services())


class PoliciesView(APIView):
    """
    Read or save the shipping, return and payment policies.

    - GET: current values for pre-filling the form.
    - PUT: create or update all three policies on eBay.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the current policy values."""
        return Response(account.current_policies())

    def put(self, request):
        """Validate the form and save the policies on eBay."""
        serializer = PolicyFormSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account.save_policies(serializer.validated_data)
        return Response(overview.connection_status())


class LocationSyncView(APIView):
    """Transfer the default warehouse to eBay as inventory location."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create the inventory location on eBay and return the new status."""
        locations.sync_default_location()
        return Response(overview.connection_status())
