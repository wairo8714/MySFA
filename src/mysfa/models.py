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
    product_name = models.CharField(
        max_length=50,
        blank=False,
        verbose_name="商品名",
        error_messages={"blank": "商品名を入力してください"},
    )
    customer_category = models.CharField(
        max_length=50,
        blank=False,
        verbose_name="顧客カテゴリ",
        error_messages={"blank": "顧客カテゴリを入力してください"},
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

    cost_price = models.IntegerField(null=True, blank=True, verbose_name="商品原価")

    price_excl_tax = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="販売価格（税抜）"
    )
    price_incl_tax = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="販売価格（税込）"
    )
    
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

    industry_code = models.CharField(max_length=50, verbose_name="業態コード")
    name = models.CharField(max_length=50, verbose_name="業態名")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return f"{self.industry_code} {self.name}"

    class Meta:
        ordering = ["group_id", "industry_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "industry_code"],
                name="uq_industrymaster_group_industry_code",
            ),
        ]

        
class JoinRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="依頼ユーザー"
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="グループ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="依頼日時")

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"

    class Meta:
        ordering = ["-created_at"]
