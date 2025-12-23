import logging
import re

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password, make_password
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

    def form_valid(self, form):
        if form.is_valid():
            user_id = form.cleaned_data.get("custom_user_id")
            logger.info(f"Received user ID: {user_id}")
            return super().form_valid(form)
        else:
            logger.error(f"Form errors: {form.errors}")
            return self.form_invalid(form)


class ForgotPasswordView(View):
    def get(self, request):
        return render(request, "forgot_password.html")

    def post(self, request):
        custom_user_id = request.POST.get("custom_user_id")
        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            request.session["custom_user_id"] = user.custom_user_id
            return render(
                request, "forgot_password.html", {"secret_question": user.question}
            )
        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーIDが見つかりません。")
            return render(request, "forgot_password.html")


class VerifyAnswerView(View):
    def post(self, request):
        custom_user_id = request.session.get("custom_user_id")
        secret_answer = request.POST.get("secret_answer")
        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            if check_password(secret_answer, user.answer):
                return render(request, "forgot_password.html", {"reset_password": True})
            else:
                messages.error(request, "秘密の質問の答えが正しくありません。")
                return render(
                    request, "forgot_password.html", {"secret_question": user.question}
                )
        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーが見つかりません。")
            return redirect("accounts:forgot_password")


class PasswordResetView(View):
    def post(self, request):
        custom_user_id = request.session.get("custom_user_id")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        custom_user_id = request.session.get("custom_user_id")
        password_pattern = re.compile(r"^(?=.*[0-9])(?=.*[a-zA-Z]).{5,15}$")
        if not password_pattern.match(new_password):
            messages.error(
                request,
                "パスワードは半角英数字を各1文字以上含む5文字以上15文字以下で入力してください。",
            )
            return render(request, "forgot_password.html", {"reset_password": True})

        if new_password != confirm_password:
            messages.error(request, "パスワードが一致しません。")
            return render(request, "forgot_password.html", {"reset_password": True})

        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            user.password1 = make_password(new_password)
            user.password2 = make_password(new_password)
            user.save()
            messages.success(request, "パスワードがリセットされました。")
            return redirect("login")
        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーIDが存在しません。")
            return redirect("accounts:forgot_password")


class CheckUserIdView(View):
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get("custom_user_id", None)
        if user_id:
            exists = CustomUser.objects.filter(custom_user_id=user_id).exists()
            if exists:
                return JsonResponse(
                    {"error": "このユーザーIDは既に使用されています。"}, status=400
                )
            else:
                return JsonResponse({"success": "このユーザーIDは使用可能です。"})
        return JsonResponse({"error": "ユーザーIDが提供されていません。"}, status=400)


class CustomLogoutView(View):
    def get(self, request):
        request.session.flush()
        logout(request)
        return redirect("home")


class DeleteAccountView(View):
    def get(self, request):
        if "messages" in request.session:
            del request.session["messages"]

        user = request.user
        logger.info(f"Original request.user: {type(user)}")
        logger.info(f"request.user.is_authenticated: {user.is_authenticated}")

        if hasattr(user, "_wrapped"):
            user = user._wrapped
            logger.info(f"After _wrapped: {type(user)}")

        try:
            if user.is_authenticated:
                logger.info(
                    f"User is authenticated, custom_user_id: "
                    f"{getattr(user, 'custom_user_id', 'Not found')}"
                )
                fresh_user = CustomUser.objects.get(custom_user_id=user.custom_user_id)
                logger.info(
                    f"Fresh user retrieved: {type(fresh_user)}, "
                    f"ID: {fresh_user.custom_user_id}"
                )
            else:
                logger.info("User is not authenticated")
                fresh_user = None
        except (CustomUser.DoesNotExist, AttributeError) as e:
            logger.error(f"Error getting fresh user: {e}")
            fresh_user = None

        context = {
            "debug": True,
            "user": fresh_user if fresh_user else user,
            "user_type": (
                type(fresh_user).__name__ if fresh_user else type(user).__name__
            ),
            "verification_result": None,
        }

        logger.info(f"Final context user: {type(context['user'])}")
        if context["user"]:
            logger.info(
                f"Final user ID: "
                f"{getattr(context['user'], 'custom_user_id', 'Not found')}"
            )

        return render(request, "registration/delete_account.html", context)

    def post(self, request):
        password = request.POST.get("password")

        user = request.user
        logger.info(f"POST - Original request.user: {type(user)}")
        logger.info(f"POST - request.user.is_authenticated: {user.is_authenticated}")

        if hasattr(user, "_wrapped"):
            user = user._wrapped
            logger.info(f"POST - After _wrapped: {type(user)}")

        try:
            if user.is_authenticated:
                logger.info(
                    f"POST - User is authenticated, custom_user_id: "
                    f"{getattr(user, 'custom_user_id', 'Not found')}"
                )
                fresh_user = CustomUser.objects.get(custom_user_id=user.custom_user_id)
                logger.info(
                    f"POST - Fresh user retrieved: {type(fresh_user)}, "
                    f"ID: {fresh_user.custom_user_id}"
                )
            else:
                logger.info("POST - User is not authenticated")
                messages.error(request, "ユーザーが認証されていません。")
                return render(request, "registration/delete_account.html")
        except (CustomUser.DoesNotExist, AttributeError) as e:
            logger.error(f"POST - Error getting fresh user: {e}")
            messages.error(request, "ユーザー情報の取得に失敗しました。")
            return render(request, "registration/delete_account.html")

        logger.info(f"Delete account attempt for user: {fresh_user.custom_user_id}")
        logger.info(f"User model type: {type(fresh_user)}")
        logger.info(f"User fields: {[field.name for field in fresh_user._meta.fields]}")
        logger.info(f"Password field exists: {hasattr(fresh_user, 'password1')}")
        logger.info(
            f"Password1 field value: "
            f"{getattr(fresh_user, 'password1', 'Not found')}"
        )
        logger.info(
            f"Standard password field exists: {hasattr(fresh_user, 'password')}"
        )
        logger.info(
            f"Standard password field value: "
            f"{getattr(fresh_user, 'password', 'Not found')}"
        )

        password_verified = False
        verification_method = None

        if hasattr(fresh_user, "password1") and fresh_user.password1:
            try:
                if check_password(password, fresh_user.password1):
                    password_verified = True
                    verification_method = "password1 field"
                    logger.info(
                        "Password verification successful using password1 field"
                    )
                else:
                    logger.info("Password verification failed using password1 field")
            except Exception as e:
                logger.error(f"Error checking password with password1: {e}")

        if not password_verified:
            try:
                if fresh_user.check_password(password):
                    password_verified = True
                    verification_method = "Django's check_password"
                    logger.info(
                        "Password verification successful using Django's check_password"
                    )
                else:
                    logger.info(
                        "Password verification failed using Django's check_password"
                    )
            except Exception as e:
                logger.error(f"Error checking password with Django's method: {e}")

        if not password_verified and hasattr(fresh_user, "password1"):
            try:
                latest_user = CustomUser.objects.get(
                    custom_user_id=fresh_user.custom_user_id
                )
                if check_password(password, latest_user.password1):
                    password_verified = True
                    verification_method = "latest user data"
                    logger.info(
                        "Password verification successful using latest user data"
                    )
                else:
                    logger.info("Password verification failed using latest user data")
            except Exception as e:
                logger.error(f"Error checking password with latest user data: {e}")

        logger.info(f"Final password verification result: {password_verified}")
        if password_verified:
            logger.info(f"Verification method used: {verification_method}")

        if password_verified:
            logger.info(
                f"Password verification successful for user: "
                f"{fresh_user.custom_user_id}"
            )
            try:
                logger.info(f"About to delete user: {fresh_user.custom_user_id}")

                fresh_user.delete()
                logger.info(f"User {fresh_user.custom_user_id} deleted successfully")

                try:
                    check_user = CustomUser.objects.get(
                        custom_user_id=fresh_user.custom_user_id
                    )
                    logger.warning(
                        f"User still exists after deletion: {check_user.custom_user_id}"
                    )
                except CustomUser.DoesNotExist:
                    logger.info(
                        f"User {fresh_user.custom_user_id} "
                        f"confirmed deleted from database"
                    )

                request.session.flush()
                logout(request)
                messages.success(request, "アカウントが削除されました。")
                return redirect("home")
            except Exception as e:
                logger.error(f"Error deleting user: {e}")
                messages.error(request, "アカウントの削除中にエラーが発生しました。")
                return render(request, "registration/delete_account.html")
        else:
            logger.warning(
                f"All password verification methods failed for user: "
                f"{fresh_user.custom_user_id}"
            )

            context = {
                "debug": True,
                "user": fresh_user,
                "user_type": type(fresh_user).__name__,
                "verification_result": {
                    "verified": False,
                    "method": "None",
                    "password_length": len(password) if password else 0,
                },
            }

            messages.error(request, "パスワードが正しくありません。")
            return render(request, "registration/delete_account.html", context)
