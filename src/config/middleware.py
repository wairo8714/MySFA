from datetime import datetime

from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TrialExpiryMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        custom_user_id = getattr(request.user, "custom_user_id", "")
        if not custom_user_id or not custom_user_id.startswith("trial"):
            return None

        expires_at_str = request.session.get("trial_expires_at")
        if not expires_at_str:
            self._cleanup_trial(request)
            return redirect("home")

        try:
            expires_at = datetime.fromtimestamp(float(expires_at_str), tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            self._cleanup_trial(request)
            return redirect("home")

        if timezone.now() >= expires_at:
            self._cleanup_trial(request)
            return redirect("home")

        return None

    def _cleanup_trial(self, request):
        request.session.flush()
        logout(request)


class HealthCheckMiddleware(MiddlewareMixin):
    """
    ヘルスチェックエンドポイントでSSLリダイレクトを無効化するミドルウェア
    ALBのヘルスチェックはHTTPで行われるため、301リダイレクトを防ぐ
    """

    def process_request(self, request):
        # ヘルスチェックエンドポイントの場合は、SSLリダイレクトを無効化
        if request.path == "/health/":
            # SECURE_SSL_REDIRECTを一時的に無効化
            # これはprocess_responseで処理する
            return None
        return None

    def process_response(self, request, response):
        # ヘルスチェックエンドポイントで301リダイレクトが発生した場合、200を返す
        if request.path == "/health/" and response.status_code == 301:
            return JsonResponse({"status": "healthy"}, status=200)
        return response
