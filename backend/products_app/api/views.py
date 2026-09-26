"""API views for the products app."""

from rest_framework import generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from core.pagination import OptionalPagePagination
from products_app.models import Category, Product, ProductImage

from .serializers import CategorySerializer, ProductImageSerializer, ProductSerializer

ARCHIVE_STATES = [Product.Status.SOLD, Product.Status.ARCHIVED]


def _product_queryset():
    """Return products with category and images preloaded (avoids N+1 queries)."""
    return (
        Product.objects.select_related("category", "category__parent")
        .prefetch_related("images")
        .order_by("-created_at")
    )


class CategoryList(generics.ListCreateAPIView):
    """List all categories or create a new one."""

    queryset = Category.objects.select_related("parent")
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single category."""

    queryset = Category.objects.select_related("parent")
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class ProductList(generics.ListCreateAPIView):
    """
    List and create products.

    - GET: active products by default; ?view=archive|all switches the scope,
      ?page=N enables pagination.
    - POST: create a new product.
    """

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagePagination

    def get_queryset(self):
        """Return the product scope selected by the ?view= parameter."""
        view = self.request.query_params.get("view", "active")
        if view == "archive":
            return _product_queryset().filter(status__in=ARCHIVE_STATES)
        if view == "all":
            return _product_queryset()
        return _product_queryset().exclude(status__in=ARCHIVE_STATES)


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a single product."""

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return products with their related data preloaded."""
        return _product_queryset()


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
