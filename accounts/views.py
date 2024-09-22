from django.urls import reverse_lazy
from django.views import generic
from .forms import CustomUserCreationForm
from django.http import JsonResponse, HttpResponse, Http404
from .models import CustomUser
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.views import View
from django.contrib.auth.models import User
from django.contrib import messages
import logging
from django.contrib.auth.hashers import check_password, make_password
import re

logger = logging.getLogger(__name__)

class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        if form.is_valid():
            user_id = form.cleaned_data.get('custom_user_id')
            logger.info(f"Received user ID: {user_id}")
            return super().form_valid(form)
        else:
            logger.error(f"Form errors: {form.errors}")
            return self.form_invalid(form)

class ForgotPasswordView(View):
    def get(self, request):
        return render(request, 'forgot_password.html')

    def post(self, request):
        custom_user_id = request.POST.get('custom_user_id')
        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            request.session['custom_user_id'] = user.custom_user_id
            return render(request, 'forgot_password.html', {'secret_question': user.question})
        except CustomUser.DoesNotExist:
            messages.error(request, 'ユーザーIDが見つかりません。')
            return render(request, 'forgot_password.html')

class VerifyAnswerView(View):
    def post(self, request):
        custom_user_id = request.session.get('custom_user_id')
        secret_answer = request.POST.get('secret_answer')
        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            if check_password(secret_answer, user.answer):
                return render(request, 'forgot_password.html', {'reset_password': True})
            else:
                messages.error(request, '秘密の質問の答えが正しくありません。')
                return render(request, 'forgot_password.html', {'secret_question': user.question})
        except CustomUser.DoesNotExist:
            messages.error(request, 'ユーザーが見つかりません。')
            return redirect('accounts:forgot_password')

class PasswordResetView(View):
    def post(self, request):
        custom_user_id = request.session.get('custom_user_id')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        custom_user_id = request.session.get('custom_user_id')
        password_pattern = re.compile(r'^(?=.*[0-9])(?=.*[a-zA-Z]).{5,15}$')
        if not password_pattern.match(new_password):
            messages.error(request, 'パスワードは半角英数字を各1文字以上含む5文字以上15文字以下で入力してください。')
            return render(request, 'forgot_password.html', {'reset_password': True})

        if new_password != confirm_password:
            messages.error(request, 'パスワードが一致しません。')
            return render(request, 'forgot_password.html', {'reset_password': True})

        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            user.password1 = make_password(new_password)
            user.password2 = make_password(new_password)
            user.save()
            messages.success(request, 'パスワードがリセットされました。')
            return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'ユーザーIDが存在しません。')
            return redirect('accounts:forgot_password')

class CheckUserIdView(View):
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get('custom_user_id', None)
        if user_id:
            exists = CustomUser.objects.filter(custom_user_id=user_id).exists()
            if exists:
                return JsonResponse({'error': 'このユーザーIDは既に使用されています。'}, status=400)
            else:
                return JsonResponse({'success': 'このユーザーIDは使用可能です。'})
        return JsonResponse({'error': 'ユーザーIDが提供されていません。'}, status=400)
