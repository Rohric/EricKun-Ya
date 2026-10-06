"""API views for the eBay connection, the seller setup, the listings and the sales."""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import OptionalPagePagination
from ebay_app.models import EbayListing, EbayShippingProfile
from ebay_app.services import (
    account,
    assignment,
    facts,
    listings,
    locations,
    oauth,
    orders,
    overview,
    pull,
    shipping_profiles,
    taxonomy,
)
from orders_app.api.serializers import OrderSerializer
from orders_app.models import Order
from products_app.models import Product

from .serializers import (
    ConnectFinishSerializer,
    IgnoreSerializer,
    LinkSerializer,
    ListingProductSerializer,
    PolicyFormSerializer,
    PublishSerializer,
    ShipmentSerializer,
    ShippingProfileSerializer,
    UnassignedListingSerializer,
)


def _listing_response(pk, code=status.HTTP_200_OK):
    """Return the refreshed product row with its listing after an action."""
    product = listings.listing_products().get(pk=pk)
    return Response(ListingProductSerializer(product).data, status=code)


def _validated(serializer_class, request):
    """Validate the request body with a serializer and return the cleaned data."""
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def _publish_arguments(request):
    """Validate the listing dialog's data and return (category, aspects, options)."""
    serializer = PublishSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.listing_arguments()


# --- Connection ---

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


# --- Templates: shipping profiles, return/payment policy, location ---

class ShippingServicesView(APIView):
    """List the domestic shipping services eBay offers on the marketplace."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return code/name pairs for the shipping service dropdown."""
        return Response(account.shipping_services())


class ShippingProfileList(generics.ListCreateAPIView):
    """
    List the shipping profiles or create a new one.

    - GET: all profiles with the number of listings that use them.
    - POST: create the profile and its shipping policy on eBay.
    """

    serializer_class = ShippingProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return the profiles, with details adopted from eBay where they are still missing."""
        return shipping_profiles.list_profiles()

    def perform_create(self, serializer):
        """Create the eBay policy first, then store the profile."""
        serializer.instance = shipping_profiles.save_profile(EbayShippingProfile(), serializer.validated_data)


class ShippingProfileDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, change or delete one shipping profile (always together with its eBay policy)."""

    serializer_class = ShippingProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return the profiles with their listing count."""
        return shipping_profiles.list_profiles()

    def perform_update(self, serializer):
        """Update the eBay policy, then the profile."""
        shipping_profiles.save_profile(serializer.instance, serializer.validated_data)

    def perform_destroy(self, instance):
        """Delete the profile unless it is the default or still in use."""
        shipping_profiles.delete_profile(instance)


class ShippingProfileDefaultView(APIView):
    """Make one shipping profile the default."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Set the default profile and return it."""
        profile = generics.get_object_or_404(EbayShippingProfile, pk=pk)
        return Response(ShippingProfileSerializer(shipping_profiles.set_default(profile)).data)


class PoliciesView(APIView):
    """
    Read or save the return and payment policy.

    - GET: current return values for pre-filling the form.
    - PUT: create or update both policies on eBay.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the current return policy values."""
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


# --- Categories ---

class CategorySuggestionsView(APIView):
    """Suggest eBay categories for a product title."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return eBay's category suggestions for ?q=."""
        return Response(taxonomy.suggest_categories(request.query_params.get("q", "")))


class CategoryRequirementsView(APIView):
    """Describe what eBay expects from a listing in one category."""

    permission_classes = [IsAuthenticated]

    def get(self, request, category_id):
        """Return aspects and allowed condition ids; ?product=<id> adds a condition hint."""
        product_id = request.query_params.get("product", "")
        return Response(listings.requirements(category_id, product_id))


# --- Listings ---

class ListingList(generics.ListAPIView):
    """List products with the state of their eBay listing; ?scope=all|listed|unlisted."""

    serializer_class = ListingProductSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagePagination

    def get_queryset(self):
        """Return the products of the requested scope (default: all sellable products)."""
        return listings.products_in_scope(self.request.query_params.get("scope", ""))


class ListingStatesView(APIView):
    """Tell the product page on which channels each product is listed."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return {product id: [channel entries]} for all listed products."""
        return Response(listings.channel_states())


class ListingPublishView(APIView):
    """Put a product online on eBay with the chosen category, aspects and options."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Store the choices, transfer the product and publish its offer."""
        product = generics.get_object_or_404(Product, pk=pk)
        category, aspects, options = _publish_arguments(request)
        listings.publish(product, category, aspects, **options)
        return _listing_response(pk)


class ListingPreviewView(APIView):
    """Show eBay's expected listing fees before a product goes online."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Transfer item and offer unpublished and return the fees eBay calculates."""
        product = generics.get_object_or_404(Product, pk=pk)
        category, aspects, options = _publish_arguments(request)
        return Response(listings.preview(product, category, aspects, **options))


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


class ListingRefreshView(APIView):
    """Read the buyer-facing price and the sold quantity of all online listings back from eBay."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Refresh the eBay facts and return how many listings succeeded and failed."""
        return Response(facts.refresh_all())


class ListingUnlinkView(APIView):
    """Detach a product from its eBay listing without touching the listing on eBay."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Unlink the listing; if it is online it returns to the assignment view."""
        assignment.unlink(generics.get_object_or_404(Product, pk=pk))
        return _listing_response(pk)


# --- Assignment: listings found on eBay that belong to no article yet ---

class ListingPullView(APIView):
    """Fetch the seller's listings from eBay."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Mirror eBay's listings and return how many were found, linked and left open."""
        return Response(pull.pull_listings())


class UnassignedList(generics.ListAPIView):
    """List the listings that wait for an article; ?ignored=1 shows the ignored ones instead."""

    serializer_class = UnassignedListingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagePagination

    def get_queryset(self):
        """Return the open (or ignored) listings without article."""
        return assignment.unassigned(self.request.query_params.get("ignored", ""))

    def get_serializer_context(self):
        """Add the free articles once, so every row can suggest a fitting one."""
        return {**super().get_serializer_context(), "products": list(assignment.free_products())}


class UnassignedLinkView(APIView):
    """Link an unassigned listing to an existing article."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Link listing and article (a legacy listing is converted first) and return the article row."""
        listing = generics.get_object_or_404(EbayListing, pk=pk)
        product = _validated(LinkSerializer, request)["product"]
        assignment.link(listing, product)
        return _listing_response(product.pk)


class UnassignedCreateProductView(APIView):
    """Create a new article from an unassigned listing."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Create the article with a new internal number, link it and return the article row."""
        product = assignment.create_product(generics.get_object_or_404(EbayListing, pk=pk))
        return _listing_response(product.pk, status.HTTP_201_CREATED)


class UnassignedCreateAllView(APIView):
    """Create a new article for every open listing (the way to start with an empty database)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create the articles and return how many worked and how many eBay refused."""
        return Response(assignment.create_all())


class UnassignedIgnoreView(APIView):
    """Hide an unassigned listing from the assignment view, or show it again."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Set the ignore flag ({"ignored": false} shows the listing again) and return the listing."""
        listing = generics.get_object_or_404(EbayListing, pk=pk)
        assignment.ignore(listing, _validated(IgnoreSerializer, request)["ignored"])
        return Response(UnassignedListingSerializer(listing).data)


# --- Sales ---

class OrderImportView(APIView):
    """Fetch new and changed sales from eBay."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Import eBay orders and return the counts of created, paid and cancelled orders."""
        return Response(orders.import_orders())


class OrderShipView(APIView):
    """Report the shipment of an eBay order."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Send carrier and tracking number to eBay and mark the order shipped."""
        order = generics.get_object_or_404(Order, pk=pk)
        serializer = ShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        orders.report_shipment(order, **serializer.validated_data)
        return Response(OrderSerializer(order).data)


class CarrierListView(APIView):
    """List the shipping carriers that can be reported to eBay."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return code/name pairs for the carrier dropdown."""
        return Response(orders.CARRIERS)
