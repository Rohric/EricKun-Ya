"""URL patterns for the eBay app."""

from django.urls import path

from .views import (
    CarrierListView,
    CategoryRequirementsView,
    CategorySuggestionsView,
    ConnectFinishView,
    ConnectStartView,
    DisconnectView,
    EbayStatusView,
    ListingList,
    ListingPublishView,
    ListingSyncAllView,
    ListingSyncView,
    ListingWithdrawView,
    LocationSyncView,
    OrderImportView,
    OrderShipView,
    PoliciesView,
    ShippingServicesView,
)

urlpatterns = [
    path("ebay/status/", EbayStatusView.as_view(), name="ebay-status"),
    path("ebay/connect/start/", ConnectStartView.as_view(), name="ebay-connect-start"),
    path("ebay/connect/finish/", ConnectFinishView.as_view(), name="ebay-connect-finish"),
    path("ebay/disconnect/", DisconnectView.as_view(), name="ebay-disconnect"),
    path("ebay/shipping-services/", ShippingServicesView.as_view(), name="ebay-shipping-services"),
    path("ebay/policies/", PoliciesView.as_view(), name="ebay-policies"),
    path("ebay/location/sync/", LocationSyncView.as_view(), name="ebay-location-sync"),
    path("ebay/categories/suggest/", CategorySuggestionsView.as_view(), name="ebay-category-suggest"),
    path(
        "ebay/categories/<str:category_id>/requirements/",
        CategoryRequirementsView.as_view(),
        name="ebay-category-requirements",
    ),
    path("ebay/listings/", ListingList.as_view(), name="ebay-listing-list"),
    path("ebay/listings/sync-all/", ListingSyncAllView.as_view(), name="ebay-listing-sync-all"),
    path("ebay/listings/<int:pk>/publish/", ListingPublishView.as_view(), name="ebay-listing-publish"),
    path("ebay/listings/<int:pk>/sync/", ListingSyncView.as_view(), name="ebay-listing-sync"),
    path("ebay/listings/<int:pk>/withdraw/", ListingWithdrawView.as_view(), name="ebay-listing-withdraw"),
    path("ebay/orders/import/", OrderImportView.as_view(), name="ebay-order-import"),
    path("ebay/orders/<int:pk>/ship/", OrderShipView.as_view(), name="ebay-order-ship"),
    path("ebay/carriers/", CarrierListView.as_view(), name="ebay-carrier-list"),
]
