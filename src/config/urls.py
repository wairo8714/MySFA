from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_http_methods
from django.views.generic.base import TemplateView

from mysfa import api_views as mysfa_api_views

from .views import HomeView


@require_http_methods(["GET", "HEAD"])
def health_check(request):
    return JsonResponse({"status": "healthy"}, status=200)


urlpatterns = [
    path("health/", health_check, name="health"),
    path("api/health/", mysfa_api_views.health, name="api_health"),
    path("api/login/", mysfa_api_views.login_api, name="api_login"),
    path("api/logout/", mysfa_api_views.logout_api, name="api_logout"),
    path("api/me/", mysfa_api_views.me, name="api_me"),
    path("api/csrf/", mysfa_api_views.csrf, name="api_csrf"),
    path("api/posts/", mysfa_api_views.posts, name="api_posts"),
    path("api/groups/", mysfa_api_views.groups, name="api_groups"),
    path("api/posts/<int:post_id>/like/", mysfa_api_views.toggle_like, name="api_posts_like"),
    path("api/posts/<int:post_id>/comments/", mysfa_api_views.comments, name="api_posts_comments"),
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
