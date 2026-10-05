"""URL patterns for the logistics app."""

from django.urls import path

from .views import WarehouseDetail, WarehouseList

urlpatterns = [
    path("warehouses/", WarehouseList.as_view(), name="warehouse-list"),
    path("warehouses/<int:pk>/", WarehouseDetail.as_view(), name="warehouse-detail"),
]
