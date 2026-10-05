"""API views for the eBay connection, the seller setup and the listings."""

from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import OptionalPagePagination
from ebay_app.services import account, listings, locations, oauth, overview, taxonomy
from products_app.models import Product

from .serializers import (
    ConnectFinishSerializer,
    ListingProductSerializer,
    PolicyFormSerializer,
    PublishSerializer,
)

NO_QUERY = "Bitte einen Suchbegriff angeben (?q=)."


def _listing_response(pk):
    """Return the refreshed product row with its listing after an action."""
    product = listings.listing_products().get(pk=pk)
    return Response(ListingProductSerializer(product).data)


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


class CategorySuggestionsView(APIView):
    """Suggest eBay categories for a product title."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return eBay's category suggestions for ?q=."""
        query = request.query_params.get("q", "").strip()
        if not query:
            raise ValidationError(NO_QUERY)
        return Response(taxonomy.suggest_categories(query))


class CategoryRequirementsView(APIView):
    """Describe what eBay expects from a listing in one category."""

    permission_classes = [IsAuthenticated]

    def get(self, request, category_id):
        """Return the aspects to fill in and the allowed condition ids."""
        return Response(taxonomy.category_requirements(category_id))


class ListingList(generics.ListAPIView):
    """List the sellable products with the state of their eBay listing."""

    serializer_class = ListingProductSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagePagination

    def get_queryset(self):
        """Return the products that are not sold or archived."""
        return listings.active_listing_products()


class ListingPublishView(APIView):
    """Put a product online on eBay with the chosen category and aspects."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Store category and aspects, transfer the product and publish its offer."""
        product = generics.get_object_or_404(Product, pk=pk)
        serializer = PublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        category = {"id": data["category_id"], "name": data["category_name"]}
        listings.publish(product, category, data["aspects"])
        return _listing_response(pk)


class ListingSyncView(APIView):
    """Transfer a listed product's current data to eBay."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Update item and offer on eBay; an ended listing goes online again."""
        listings.sync(generics.get_object_or_404(Product, pk=pk))
        return _listing_response(pk)


class ListingWithdrawView(APIView):
    """End a product's eBay listing."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Withdraw the offer; the product itself stays untouched."""
        listings.withdraw(generics.get_object_or_404(Product, pk=pk))
        return _listing_response(pk)


class ListingSyncAllView(APIView):
    """Transfer every listing that has local changes."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Sync all changed listings and return how many succeeded and failed."""
        return Response(listings.sync_all())
