from django.urls import path
from .views import SignUpView, ForgotPasswordView, PasswordResetView, VerifyAnswerView, CheckUserIdView

app_name = 'accounts'
urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('check_user_id/', CheckUserIdView.as_view(), name='check_user_id'),
    path('forgot_password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify_answer/', VerifyAnswerView.as_view(), name='verify_answer'),
    path('reset_password/', PasswordResetView.as_view(), name='reset_password'),
]
