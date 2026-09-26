"""API views for the products app."""

from rest_framework import generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from products_app.models import Category, Product, ProductImage

from .serializers import CategorySerializer, ProductImageSerializer, ProductSerializer


class CategoryList(generics.ListCreateAPIView):
    """List all categories or create a new one."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single category."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class ProductList(generics.ListCreateAPIView):
    """List active products (or the archive with ?view=archive) and create products."""

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return active products by default; ?view=archive|all switches the scope."""
        archive = [Product.Status.SOLD, Product.Status.ARCHIVED]
        view = self.request.query_params.get("view", "active")
        if view == "archive":
            return Product.objects.filter(status__in=archive)
        if view == "all":
            return Product.objects.all()
        return Product.objects.exclude(status__in=archive)


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
