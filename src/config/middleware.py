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
        is_trial = bool(
            getattr(request.user, "is_trial", False)
        ) or custom_user_id.startswith("trial")
        if not custom_user_id or not is_trial:
            return None

        now = timezone.now()
        expires_at = getattr(request.user, "trial_expires_at", None)
        if expires_at and now >= expires_at:
            self._cleanup_trial(request)
            return redirect("home")

        if not expires_at:
            expires_at_str = request.session.get("trial_expires_at")
            if not expires_at_str:
                self._cleanup_trial(request)
                return redirect("home")
            try:
                expires_at_ts = float(expires_at_str)
            except (ValueError, TypeError, OSError):
                self._cleanup_trial(request)
                return redirect("home")
            if now.timestamp() >= expires_at_ts:
                self._cleanup_trial(request)
                return redirect("home")

        return None

    def _cleanup_trial(self, request):
        trial_user_pk = None
        try:
            user = getattr(request, "user", None)
            custom_user_id = getattr(user, "custom_user_id", "") if user else ""
            if (
                user
                and getattr(user, "is_authenticated", False)
                and custom_user_id.startswith("trial")
            ):
                trial_user_pk = user.pk
        except Exception:
            trial_user_pk = None

        request.session.flush()
        logout(request)

        if trial_user_pk:
            User = get_user_model()
            User.objects.filter(pk=trial_user_pk).delete()


class HealthCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        return None

    def process_response(self, request, response):
        if request.path == "/health/" and response.status_code == 301:
            return JsonResponse({"status": "healthy"}, status=200)
        return response
