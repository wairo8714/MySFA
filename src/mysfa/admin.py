from django.contrib import admin

from .models import (
    ChangeRequest,
    ChangeRequestRow,
    Group,
    IndustryMaster,
    JoinRequest,
    Post,
    ProductMaster,
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "group",
        "product",
        "industry",
        "created_at",
        "likes_count",
    )
    list_filter = ("group", "created_at")
    search_fields = (
        "product__product_code",
        "product__name",
        "industry__name",
        "contents",
        "user__custom_user_id",
        "user__username",
    )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "custom_id",
        "is_active",
        "is_locked",
        "is_approval",
        "creator",
    )
    list_filter = ("is_active", "is_locked", "is_approval")
    search_fields = (
        "name",
        "custom_id",
        "creator__custom_user_id",
        "creator__username",
    )


@admin.register(ProductMaster)
class ProductMasterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "group",
        "product_code",
        "name",
        "category_main",
        "category_sub",
        "updated_at",
    )
    list_filter = ("group",)
    search_fields = ("product_code", "name", "category_main", "category_sub")


@admin.register(IndustryMaster)
class IndustryMasterAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "name", "updated_at")
    list_filter = ("group",)
    search_fields = ("name",)


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "group", "created_at")
    list_filter = ("group", "created_at")
    search_fields = (
        "user__custom_user_id",
        "user__username",
        "group__name",
        "group__custom_id",
    )


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "group",
        "kind",
        "status",
        "requester",
        "approver",
        "created_at",
        "submitted_at",
        "decided_at",
    )
    list_filter = ("kind", "status", "group")
    search_fields = (
        "title",
        "note",
        "requester__custom_user_id",
        "requester__username",
        "group__name",
        "group__custom_id",
    )


@admin.register(ChangeRequestRow)
class ChangeRequestRowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "change_request",
        "row_index",
        "op",
        "code",
        "name",
        "is_valid",
    )
    list_filter = ("op", "is_valid")
    search_fields = ("code", "name", "error_code", "error_message")
