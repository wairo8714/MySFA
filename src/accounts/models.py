import os
import uuid

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import RegexValidator
from django.db import models


class CustomUser(AbstractUser):
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
    password1 = models.CharField(
        max_length=128,
        blank=False,
        verbose_name="パスワード",
        validators=[
            RegexValidator(
                r"^(?=.*[0-9])(?=.*[a-zA-Z]).{5,15}$",
                message="パスワードは半角英数字を各1文字以上含む5文字以上15文字以下で入力してください。",
            )
        ],
    )
    password2 = models.CharField(
        max_length=128,
        blank=False,
        verbose_name="パスワード確認",
        validators=[
            RegexValidator(
                r"^(?=.*[0-9])(?=.*[a-zA-Z]).{5,15}$",
                message="パスワードは半角英数字を各1文字以上含む5文字以上15文字以下で入力してください。",
            )
        ],
    )
    question = models.CharField(max_length=128, blank=False, verbose_name="秘密の質問")
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

    def clean(self):
        self.clean_password()

    def clean_password(self):
        if not self.password1 == self.password2:
            raise ValidationError("パスワードが一致していません。")
        if (
            CustomUser.objects.filter(custom_user_id=self.custom_user_id)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError("このユーザーIDは既に使用されています。")

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = CustomUser.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.profile_image != self.profile_image:
                if (
                    old_instance.profile_image
                    and old_instance.profile_image.name != "default_images/ic013.png"
                ):
                    default_storage.delete(old_instance.profile_image.name)

        self.password1 = make_password(self.password1)
        self.password2 = make_password(self.password2)
        self.answer = make_password(self.answer)

        super().save(*args, **kwargs)
