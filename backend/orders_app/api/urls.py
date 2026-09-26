"""URL patterns for the orders app."""

from django.urls import path

from .views import OrderCancelView, OrderDetail, OrderList

urlpatterns = [
    path("orders/", OrderList.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetail.as_view(), name="order-detail"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
]
