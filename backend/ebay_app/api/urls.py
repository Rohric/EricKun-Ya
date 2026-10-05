"""URL patterns for the eBay app."""

from django.urls import path

from .views import (
    ConnectFinishView,
    ConnectStartView,
    DisconnectView,
    EbayStatusView,
    LocationSyncView,
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
]
