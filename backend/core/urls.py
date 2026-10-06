"""URL configuration for the core project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as static_serve

from core.views import DashboardSummaryView

# The frontend lives in a sibling folder; Django serves it in DEBUG so the whole
# app runs from a single `runserver`. In production a real web server serves it.
FRONTEND_DIR = settings.BASE_DIR.parent / "frontend"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("auth_app.api.urls")),
    path("api/", include("products_app.api.urls")),
    path("api/", include("orders_app.api.urls")),
    path("api/", include("finance_app.api.urls")),
    path("api/", include("logistics_app.api.urls")),
    path("api/", include("ebay_app.api.urls")),
    path("api/dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
]

if settings.DEBUG:
    # Serve uploaded media before the frontend catch-all grabs the path.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("", static_serve, {"path": "index.html", "document_root": FRONTEND_DIR}),
        re_path(r"^(?P<path>.*)$", static_serve, {"document_root": FRONTEND_DIR}),
    ]
