"""URL patterns for HTTP APIs under the /api/ prefix (admin excluded)."""

from django.urls import include, path

from artiq_client.file_views import FileListView, FileReadView

urlpatterns = [
    path("", include("users.urls")),
    path("files/", FileListView.as_view(), name="files-list"),
    path("files/read/", FileReadView.as_view(), name="files-read"),
]
