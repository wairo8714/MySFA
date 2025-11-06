from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic.base import TemplateView

from .views import HomeView

urlpatterns = [
    path("health/", lambda request: JsonResponse({"status": "healthy"}), name="health"),
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "terms-of-service/",
        TemplateView.as_view(template_name="terms-of-service.html"),
        name="terms-of-service",
    ),
    path(
        "privacy-policy/",
        TemplateView.as_view(template_name="privacy-policy.html"),
        name="privacy-policy",
    ),
    path("mysfa/", include("mysfa.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
