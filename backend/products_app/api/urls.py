"""URL patterns for the products app."""

from django.urls import path

from .views import ProductDetail, ProductList

urlpatterns = [
    path("products/", ProductList.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetail.as_view(), name="product-detail"),
]
