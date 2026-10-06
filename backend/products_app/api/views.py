"""API views for the products app."""

from rest_framework import generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import OptionalPagePagination
from products_app.models import Category, Product, ProductImage
from products_app.utils import filter_products, status_counts

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

    - GET: active products by default; ?view=archive|all switches the scope, ?status= selects
      one status instead; ?category= and ?search= narrow the list; ?page=N enables pagination.
    - POST: create a new product.
    """

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagePagination

    def get_queryset(self):
        """Return the filtered products in the scope chosen by ?status= or ?view=."""
        params = self.request.query_params
        queryset = filter_products(_product_queryset(), params)
        view = "all" if params.get("status") else params.get("view", "active")
        if view == "archive":
            return queryset.filter(status__in=ARCHIVE_STATES)
        if view == "all":
            return queryset
        return queryset.exclude(status__in=ARCHIVE_STATES)


class ProductCountsView(APIView):
    """Count the products per status for the tabs of the product page."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return {all, available, reserved, sold, archived}, honouring ?category= and ?search=."""
        return Response(status_counts(request.query_params))


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
