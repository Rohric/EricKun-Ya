"""API views for the products app."""

from rest_framework import generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from products_app.models import Product, ProductImage

from .serializers import ProductImageSerializer, ProductSerializer


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


class ProductImageList(generics.ListCreateAPIView):
    """List a product's images or upload a new one (multipart)."""

    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Return the images of the product named in the URL."""
        return ProductImage.objects.filter(product_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        """Attach the image to its product and append it to the end."""
        product = generics.get_object_or_404(Product, pk=self.kwargs["pk"])
        serializer.save(product=product, position=product.images.count())


class ProductImageDetail(generics.DestroyAPIView):
    """Delete a single product image."""

    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]
