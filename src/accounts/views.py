import logging
import re

from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View, generic

from .forms import CustomUserCreationForm
from .models import CustomUser

logger = logging.getLogger(__name__)


class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"


PW_RESET_USER_ID_KEY = "pw_reset_user_id"
PW_RESET_VERIFIED_KEY = "pw_reset_verified"


def _clear_pw_reset_session(session):
    session.pop(PW_RESET_USER_ID_KEY, None)
    session.pop(PW_RESET_VERIFIED_KEY, None)
    session.pop("custom_user_id", None)


class ForgotPasswordView(View):
    def get(self, request):
        return render(request, "forgot_password.html")

    def post(self, request):
        custom_user_id = request.POST.get("custom_user_id")

        # フロー開始時、セッションをクリアにする
        _clear_pw_reset_session(request.session)

        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            request.session[PW_RESET_USER_ID_KEY] = user.custom_user_id
            request.session[PW_RESET_VERIFIED_KEY] = False
            return render(
                request,
                "forgot_password.html",
                {"secret_question": user.question},
            )
        except CustomUser.DoesNotExist:
            messages.error(request, "入力内容をご確認下さい。")
            return render(request, "forgot_password.html")


class VerifyAnswerView(View):
    def post(self, request):
        custom_user_id = request.session.get(
            PW_RESET_USER_ID_KEY
        ) or request.session.get("custom_user_id")
        secret_answer = request.POST.get("secret_answer")

        if not custom_user_id:
            messages.error(request, "最初からやり直してください")
            return redirect("accounts:forgot_password")

        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            if check_password(secret_answer, user.answer):
                request.session[PW_RESET_VERIFIED_KEY] = True

                # セッション固定攻撃対策
                request.session.cycle_key()
                return render(
                    request,
                    "forgot_password.html",
                    {"reset_password": True},
                )

            request.session[PW_RESET_VERIFIED_KEY] = False
            messages.error(
                request,
                "秘密の質問の答えが正しくありません。",
            )

            return render(
                request,
                "forgot_password.html",
                {"secret_question": user.question},
            )

        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーが見つかりません。")
            _clear_pw_reset_session(request.session)
            return redirect("accounts:forgot_password")


class PasswordResetView(View):
    def post(self, request):
        custom_user_id = request.session.get(
            PW_RESET_USER_ID_KEY
        ) or request.session.get("custom_user_id")
        verified = request.session.get(PW_RESET_VERIFIED_KEY) is True

        if not custom_user_id or not verified:
            messages.error(
                request,
                "問題が発生しました。やり直してください。",
            )
            _clear_pw_reset_session(request.session)
            return redirect("accounts:forgot_password")

        new_password = request.POST.get("new_password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        password_pattern = re.compile(r"^(?=.*[0-9])(?=.*[a-zA-Z]).{5,20}$")
        if not password_pattern.match(new_password or ""):
            messages.error(
                request,
                "パスワードは半角英数字を各1文字以上含む5文字以上20文字以下で入力してください。",
            )
            return render(
                request,
                "forgot_password.html",
                {"reset_password": True},
            )

        if new_password != confirm_password:
            messages.error(request, "パスワードが一致しません。")
            return render(
                request,
                "forgot_password.html",
                {"reset_password": True},
            )

        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            user.set_password(new_password)

            user.save()
            _clear_pw_reset_session(request.session)
            messages.success(request, "パスワードがリセットされました。")
            return redirect("login")

        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーIDが存在しません。")
            _clear_pw_reset_session(request.session)
            return redirect("accounts:forgot_password")


class CheckUserIdView(View):
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get("custom_user_id", None)
        if user_id:
            exists = CustomUser.objects.filter(custom_user_id=user_id).exists()
            if exists:
                return JsonResponse(
                    {"error": "このユーザーIDは既に使用されています。"},
                    status=400,
                )
            else:
                return JsonResponse({"success": "このユーザーIDは使用可能です。"})
        return JsonResponse(
            {"error": "ユーザーIDが提供されていません。"},
            status=400,
        )


class CustomLogoutView(View):
    def get(self, request):
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

        # trialユーザーはログアウト時にDBからも削除
        if trial_user_pk:
            CustomUser.objects.filter(pk=trial_user_pk).delete()

        return redirect("home")


class DeleteAccountView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")

        return render(
            request,
            "registration/delete_account.html",
            {"user": request.user},
        )

    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "ログインしてください。")
            return redirect("login")

        password = request.POST.get("password") or ""
        if not password:
            messages.error(request, "パスワードを入力してください。")
            return render(
                request,
                "registration/delete_account.html",
                {"user": request.user},
            )

        try:
            fresh_user = CustomUser.objects.get(pk=request.user.pk)
        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーが見つかりません。")
            return redirect("home")

        password_verified = fresh_user.check_password(password)

        if not password_verified:
            messages.error(request, "パスワードが正しくありません。")
            return render(
                request,
                "registration/delete_account.html",
                {"user": fresh_user},
            )

        # グループのcreatorが削除された際は、別のグループメンバーに権限を委譲する
        from mysfa.models import Group, GroupMembership

        User = get_user_model()

        for group in Group.objects.filter(creator=fresh_user):
            members = (
                User.objects.filter(
                    groupmembership__group=group,
                    groupmembership__is_active=True,
                )
                .exclude(pk=fresh_user.pk)
                .order_by("custom_user_id")
                .distinct()
            )

            if members.exists():
                group.creator = members.first()
                group.is_active = True
                group.save(update_fields=["creator", "is_active"])
            else:
                group.creator = None
                group.is_active = False
                group.save(update_fields=["creator", "is_active"])

        for group in Group.objects.filter(
            memberships__user=fresh_user,
            memberships__is_active=True,
        ).distinct():
            GroupMembership.objects.filter(
                group=group,
                user=fresh_user,
                is_active=True,
            ).update(is_active=False)

            if not GroupMembership.objects.filter(group=group, is_active=True).exists():
                group.creator = None
                group.is_active = False
                group.save(update_fields=["creator", "is_active"])

        fresh_user.delete()
        request.session.flush()
        logout(request)
        messages.success(request, "アカウントが削除されました。")
        return redirect("home")
