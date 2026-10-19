from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.surveys.api.urls")),
    # shortcut: local demo assets; serve STATIC_ROOT through a web server in production.
    path("static/<path:path>", serve, {"document_root": settings.STATIC_ROOT}),
]
