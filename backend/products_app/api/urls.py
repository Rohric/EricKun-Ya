"""URL patterns for the products app."""

from django.urls import path

from .views import (
    CategoryDetail,
    CategoryList,
    ProductDetail,
    ProductImageDetail,
    ProductImageList,
    ProductList,
)

urlpatterns = [
    path("categories/", CategoryList.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetail.as_view(), name="category-detail"),
    path("products/", ProductList.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetail.as_view(), name="product-detail"),
    path("products/<int:pk>/images/", ProductImageList.as_view(), name="product-image-list"),
    path("product-images/<int:pk>/", ProductImageDetail.as_view(), name="product-image-detail"),
]
