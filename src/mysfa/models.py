import os
import random
import uuid

from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.db import models


class Post(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="投稿者", on_delete=models.CASCADE
    )
    group = models.ForeignKey(
        AuthGroup, on_delete=models.CASCADE, verbose_name="グループ"
    )
    product = models.ForeignKey(
        "ProductMaster",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="商品",
    )
    industry = models.ForeignKey(
        "IndustryMaster",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="業態",
    )
    trial_session_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="トライアルセッションID",
    )
    contents = models.TextField(
        verbose_name="投稿文",
        max_length=100,
        error_messages={"max_length": "100文字以内で入力してください"},
    )
    image = models.ImageField(
        upload_to="post_images/", blank=True, null=True, verbose_name="投稿画像"
    )
    likes_count = models.IntegerField(default=0, verbose_name="いいね数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="投稿日時")
    liked_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True,
        verbose_name="いいねしたユーザー",
    )

    @property
    def product_name(self) -> str:
        """
        互換用（旧: product_name CharField）。
        テンプレ側で `post.product_name` を参照していても壊れないようにする。
        """
        return self.product.name if self.product_id else ""

    @property
    def customer_category(self) -> str:
        """
        互換用（旧: customer_category CharField / 画面上の業態）。
        """
        return self.industry.name if self.industry_id else ""

    def __str__(self):
        return self.product_name

    class Meta:
        ordering = ["-created_at"]

class Group(AuthGroup):
    custom_id = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        default="00000000",
        verbose_name="グループID",
    )
    is_active = models.BooleanField(default=True, verbose_name="有効フラグ")
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="user_groups",
        verbose_name="グループメンバー",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        related_name="created_groups",
        on_delete=models.SET_NULL,
        verbose_name="グループ作成者",
    )
    icon = models.ImageField(
        upload_to="group_icon_path",
        default="default_images/702.png",
        blank=True,
        null=True,
        verbose_name="グループアイコン",
    )
    is_locked = models.BooleanField(default=False, verbose_name="ロック機能")
    is_approval = models.BooleanField(default=False, verbose_name="承認機能")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.custom_id or self.custom_id == "00000000":
            self.custom_id = self.generate_unique_id()
        super().save(*args, **kwargs)

    def generate_unique_id(self):
        while True:
            new_id = "".join([str(random.randint(0, 9)) for _ in range(8)])
            if not Group.objects.filter(custom_id=new_id).exists():
                return new_id

    def group_icon_path(self, filename):
        ext = filename.split(",")[-1]
        unique_filename = f"{self.custom_id}_{uuid.uuid4()}.{ext}"
        return os.path.join("group_icons/", unique_filename)


class ProductMaster(models.Model):
    group = models.ForeignKey(
        "Group",
        on_delete=models.CASCADE,
        related_name="product_masters",
        verbose_name="グループ",
    )

    product_code = models.CharField(max_length=50, verbose_name="商品コード")
    name = models.CharField(max_length=50, verbose_name="商品名")

    category_main = models.CharField(max_length=50, null=True, blank=True, verbose_name="大分類")
    category_sub = models.CharField(max_length=50, null=True, blank=True, verbose_name="小分類")
    
    custom_text_1 = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="自由項目（文字1）"
    )
    custom_text_2 = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="自由項目（文字2）"
    )
    custom_text_3 = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="自由項目（文字3）"
    )

    custom_int_1 = models.IntegerField(null=True, blank=True, verbose_name="自由項目（数値1）")
    custom_int_2 = models.IntegerField(null=True, blank=True, verbose_name="自由項目（数値2）")

    custom_date_1 = models.DateField(null=True, blank=True, verbose_name="自由項目（日付1）")

    description = models.TextField(null=True, blank=True, verbose_name="自由記入")

    is_active = models.BooleanField(default=True, verbose_name="有効フラグ")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return f"{self.product_code} {self.name}"

    class Meta:
        ordering = ["group_id", "product_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "product_code"],
                name="uq_productmaster_group_product_code",
            ),
        ]


class IndustryMaster(models.Model):
    group = models.ForeignKey(
        "Group",
        on_delete=models.CASCADE,
        related_name="industry_masters",
        verbose_name="グループ",
    )
    name = models.CharField(max_length=50, verbose_name="業態名")
    is_active = models.BooleanField(default=True, verbose_name="有効フラグ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return f"{self.id} {self.name}"

    class Meta:
        ordering = ["group_id", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "name"],
                name="uq_industrymaster_group_name",
            ),
        ]


class ChangeRequest(models.Model):
    class Kind(models.TextChoices):
        PRODUCT = "PRODUCT", "商品"
        INDUSTRY = "INDUSTRY", "業態"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "下書き"
        PENDING = "PENDING", "承認待ち"
        APPROVED = "APPROVED", "承認済み(反映済み)"
        REJECTED = "REJECTED", "却下"

    group = models.ForeignKey(
        "Group",
        on_delete=models.CASCADE,
        related_name="change_requests",
        verbose_name="対象グループ",
    )
    trial_session_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="トライアルセッションID",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name="種別")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="ステータス",
    )

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="change_requests_requested",
        verbose_name="依頼者",
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_requests_approved",
        verbose_name="承認者",
    )

    title = models.CharField(max_length=100, blank=True, default="", verbose_name="タイトル")
    note = models.TextField(blank=True, default="", verbose_name="メモ")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="依頼日時")
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="承認/却下日時")

    def __str__(self):
        return f"{self.group_id} {self.kind} {self.status} ({self.id})"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["group", "kind", "status"]),
            models.Index(fields=["group", "created_at"]),
            models.Index(fields=["trial_session_id"]),
        ]


class ChangeRequestRow(models.Model):
    class Op(models.TextChoices):
        UPSERT = "UPSERT", "追加/更新"
        DELETE = "DELETE", "削除"

    change_request = models.ForeignKey(
        ChangeRequest,
        on_delete=models.CASCADE,
        related_name="rows",
        verbose_name="変更依頼",
    )
    trial_session_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="トライアルセッションID",
    )
    row_index = models.PositiveIntegerField(verbose_name="行番号(1始まり)")
    op = models.CharField(max_length=10, choices=Op.choices, verbose_name="操作")

    code = models.CharField(max_length=50, verbose_name="コード")
    name = models.CharField(max_length=50, blank=True, default="", verbose_name="名称")

    is_valid = models.BooleanField(default=True, verbose_name="取込可能")
    error_code = models.CharField(max_length=50, blank=True, default="", verbose_name="エラーコード")
    error_message = models.TextField(blank=True, default="", verbose_name="エラーメッセージ")

    diff_json = models.JSONField(null=True, blank=True, verbose_name="差分(JSON)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    def __str__(self):
        return f"{self.change_request_id} #{self.row_index} {self.op} {self.code}"

    class Meta:
        ordering = ["row_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["change_request", "row_index"],
                name="uq_change_request_row_change_request_row_index",
            ),
        ]
        indexes = [
            models.Index(fields=["change_request", "is_valid"]),
            models.Index(fields=["change_request", "code"]),
        ]


class JoinRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="依頼ユーザー"
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="グループ")
    trial_session_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="トライアルセッションID",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="依頼日時")

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"

    class Meta:
        ordering = ["-created_at"]
