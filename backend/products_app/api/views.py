"""API views for the products app."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from products_app.models import Product

from .serializers import ProductSerializer


class ProductList(generics.ListCreateAPIView):
    """List all products or create a new one."""

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single product."""

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
