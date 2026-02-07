from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UserIdBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        User = get_user_model()

        user = User.objects.filter(custom_user_id=username).first()
        if user is None:
            return None

        if not self.user_can_authenticate(user):
            return None

        return user if user.check_password(password) else None
