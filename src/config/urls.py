from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_http_methods
from django.views.generic.base import TemplateView

from mysfa import api_views as mysfa_api_views

from .views import HomeView


# ヘルスチェック用のビュー（ALLOWED_HOSTSのチェックをバイパス）
@require_http_methods(["GET", "HEAD"])
def health_check(request):
    # ヘルスチェックは常に成功を返す（ALLOWED_HOSTSのチェックをバイパス）
    return JsonResponse({"status": "healthy"}, status=200)


urlpatterns = [
    path("health/", health_check, name="health"),
    path("api/health/", mysfa_api_views.health, name="api_health"),
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
