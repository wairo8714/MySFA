from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

DEMO_ALLOWED_POST_PATH_PREFIXES = ("/mysfa/like-post/",)


class DemoReadOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_demo = request.session.get("is_demo", False)
        if not is_demo:
            return self.get_response(request)

        if request.method in SAFE_METHODS:
            return self.get_response(request)

        # demo中でも許可するPOST（ここだけ通す）
        if request.method == "POST" and request.path_info.startswith(
            DEMO_ALLOWED_POST_PATH_PREFIXES
        ):
            return self.get_response(request)

        # それ以外の書き込み系はブロック
        login_url = reverse("login")
        content_type = request.headers.get("Content-Type", "")
        accept = request.headers.get("Accept", "")
        if "application/json" in content_type or "application/json" in accept:
            return JsonResponse({"redirect": login_url}, status=401)

        return redirect(login_url)
