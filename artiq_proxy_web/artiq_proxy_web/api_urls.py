"""URL patterns for HTTP APIs under the /api/ prefix (admin excluded)."""

from django.urls import include, path

urlpatterns = [
    path("", include("users.urls")),
]
