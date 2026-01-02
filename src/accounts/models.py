import os
import uuid

from django.contrib.auth.hashers import identify_hasher, make_password
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import RegexValidator
from django.db import models


class CustomUser(AbstractUser):
    username = models.CharField(max_length=20, blank=False, null=False, unique=False)

    USERNAME_FIELD = "custom_user_id"
    REQUIRED_FIELDS = ["username"]
    
    custom_user_id = models.CharField(
        primary_key=True,
        max_length=15,
        null=False,
        unique=True,
        blank=False,
        verbose_name="ユーザーID",
        validators=[
            RegexValidator(
                r"^[0-9a-zA-Z]+$", message="userIDは半角英数字のみ使用できます。"
            )
        ],
    )

    question = models.CharField(max_length=20, blank=False, verbose_name="秘密の質問")

    answer = models.CharField(max_length=128, blank=False, verbose_name="答え")

    def user_profile_image_path(self, filename):
        ext = filename.split(".")[-1]
        unique_filename = f"{self.custom_user_id}_{uuid.uuid4()}.{ext}"
        return os.path.join("profile_images", unique_filename)

    profile_image = models.ImageField(
        upload_to=user_profile_image_path,
        default="default_images/ic013.png",
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = CustomUser.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.profile_image != self.profile_image:
                if (
                    old_instance.profile_image
                    and old_instance.profile_image.name != "default_images/ic013.png"
                ):
                    default_storage.delete(old_instance.profile_image.name)

        def is_hashed(value: str) -> bool:
            try:
                identify_hasher(value)
                return True
            except Exception:
                return False

        if self.answer and not is_hashed(self.answer):
            self.answer = make_password(self.answer)

        super().save(*args, **kwargs)
