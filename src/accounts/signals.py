from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver


@receiver(user_logged_out)
def delete_trial_user_on_logout(sender, request, user, **kwargs):
    if not user:
        return

    custom_user_id = getattr(user, "custom_user_id", "") or ""
    is_trial = bool(getattr(user, "is_trial", False)) or custom_user_id.startswith("trial")
    if not is_trial:
        return

    User = get_user_model()
    User.objects.filter(pk=user.pk).delete()

