from django.conf import settings
from django.shortcuts import redirect, render
from django.views import View


class HomeView(View):
    def get(self, request):
        user_groups = None

        if request.user.is_authenticated:
            user_groups = request.user.groups.all()
            if user_groups.exists():
                return redirect("mysfa:timeline")

        return render(
            request,
            "home.html",
            {"user_groups": user_groups, "MEDIA_URL": settings.MEDIA_URL},
        )
