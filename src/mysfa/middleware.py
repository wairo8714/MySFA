from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

class DemoReadOnlyMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    is_demo = request.session.get("is_demo", False)

    if is_demo and request.method not in SAFE_METHODS:
      login_url = reverse("login")

      content_type = request.headers.get("Content=Type", "")
      if "application/json" in contnt_type:
        return JsonResponse({"redirect": login_url}, status=401)

      return redirect(login_url)

    return self.get_response(request)
    
