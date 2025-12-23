from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UserIdOrUsernameBackend(ModelBackend):
    """
    ログインフォームの username 欄で「ユーザー名(username)」でも
    「ユーザーID(custom_user_id)」でもログインできるようにする。
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        User = get_user_model()

        user = User.objects.filter(custom_user_id=username).first()
        if user is None:
            user = User.objects.filter(username=username).first()

        if user is None:
            return None

        if not self.user_can_authenticate(user):
            return None

        if user.check_password(password):
            return user

        return None
