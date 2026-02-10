from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    ordering = ("custom_user_id",)
    list_display = (
        "custom_user_id",
        "username",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("custom_user_id", "username")

    fieldsets = (
        (None, {"fields": ("custom_user_id", "password")}),
        ("基本情報", {"fields": ("username", "profile_image")}),
        (
            "権限",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("日時", {"fields": ("last_login", "date_joined")}),
        ("秘密の質問", {"fields": ("question", "answer")}),
    )
    readonly_fields = ("last_login", "date_joined")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "custom_user_id",
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "question",
                    "answer",
                    "profile_image",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
