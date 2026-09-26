"""Opt-in pagination: list endpoints paginate only when a ?page= parameter is sent."""

from rest_framework.pagination import PageNumberPagination


class OptionalPagePagination(PageNumberPagination):
    """Paginate when the client asks for a page; otherwise return the full list."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """Skip pagination when no page parameter is present."""
        if self.page_query_param not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)
