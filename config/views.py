from django.views import View
from django.shortcuts import redirect, render
from django.conf import settings
from snsapp.models import Group  # Group モデルをインポート

class HomeView(View):
    def get(self, request):
        # ユーザーがグループに所属しているか確認
        user_groups = request.user.groups.all()
        if user_groups.exists():
            return redirect('snsapp:timeline')
        # グループに所属していない場合は home.html をレンダリング
        return render(request, 'home.html', {'user_groups': user_groups})
    
    def home(request):
        context = {
            'MEDIA_URL': settings.MEDIA_URL,
        }
        return render(request, 'home.html', context)