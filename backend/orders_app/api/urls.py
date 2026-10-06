"""URL patterns for the orders app."""

from django.urls import path

from .views import OrderCancelView, OrderDetail, OrderList, ProductSalesView

urlpatterns = [
    path("orders/", OrderList.as_view(), name="order-list"),
    path("orders/product-sales/", ProductSalesView.as_view(), name="order-product-sales"),
    path("orders/<int:pk>/", OrderDetail.as_view(), name="order-detail"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
]
