from django.urls import path

from .views import (
    CheckUserIdView,
    CustomLogoutView,
    DeleteAccountView,
    ForgotPasswordView,
    PasswordResetView,
    SignUpView,
    VerifyAnswerView,
)

app_name = "accounts"

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("forgot_password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("verify_answer/", VerifyAnswerView.as_view(), name="verify_answer"),
    path("reset_password/", PasswordResetView.as_view(), name="reset_password"),
    path("check_user_id/", CheckUserIdView.as_view(), name="check_user_id"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("delete_account/", DeleteAccountView.as_view(), name="delete_account"),
]
