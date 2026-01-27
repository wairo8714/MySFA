from django.contrib.auth import get_user_model, logout
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
            expires_at_ts = float(expires_at_str)
        except (ValueError, TypeError, OSError):
            self._cleanup_trial(request)
            return redirect("home")

        now_ts = timezone.now().timestamp()
        if now_ts >= expires_at_ts:
            self._cleanup_trial(request)
            return redirect("home")

        return None

    def _cleanup_trial(self, request):
        trial_user_pk = None
        try:
            user = getattr(request, "user", None)
            custom_user_id = getattr(user, "custom_user_id", "") if user else ""
            if user and getattr(user, "is_authenticated", False) and custom_user_id.startswith("trial"):
                trial_user_pk = user.pk
        except Exception:
            trial_user_pk = None

        request.session.flush()
        logout(request)

        # trialユーザーはログアウト時にDBからも削除（投稿などもFKで連動削除される）
        if trial_user_pk:
            User = get_user_model()
            User.objects.filter(pk=trial_user_pk).delete()


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
