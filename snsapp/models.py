import random
import os
import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup

class MyModel(models.Model):
    file = models.FileField(upload_to='uploads/')

    def __str__(self):
        return self.file.name

class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='投稿者',on_delete=models.CASCADE)
    product_name = models.CharField(max_length=50, blank=False, verbose_name='商品名', error_messages={'blank':'商品名を入力してください'})
    customer_category = models.CharField(max_length=50, blank=False, verbose_name='顧客カテゴリ', error_messages={'blank':'顧客カテゴリを入力してください'})
    contents = models.TextField(verbose_name='投稿文', max_length=100, error_messages={'max_length':'100文字以内で入力してください'})
    group = models.ForeignKey(AuthGroup, on_delete=models.CASCADE, verbose_name='グループ')  
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='投稿日時')

    def __str__(self):
        return self.product_name
    
    class Meta:
        ordering = ["-created_at"]

class Group(AuthGroup):
    custom_id = models.CharField(max_length=8, unique=True, blank=True, default='00000000', verbose_name='グループID')
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='user_groups', verbose_name='グループメンバー') 
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name='created_groups', on_delete=models.CASCADE, verbose_name='グループ作成者')
    icon = models.ImageField(upload_to='group_icon_path', default='default_images/702.png', blank=True, verbose_name='グループアイコン')
    is_locked = models.BooleanField(default=False, verbose_name='ロック機能')
    is_approval = models.BooleanField(default=False, verbose_name='承認機能')

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.custom_id or self.custom_id == '00000000':
            self.custom_id = self.generate_unique_id()
        super().save(*args, **kwargs)

    def generate_unique_id(self):
        while True:
            new_id = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            if not Group.objects.filter(custom_id=new_id).exists():
                return new_id
            
    def group_icon_path(self, filename):
        ext = filename.split(',')[-1]
        unique_filename = f"{self.custom_id}_{uuid.uuid4()}.{ext}"
        return os.path.join('group_icons/', unique_filename)
    
class JoinRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='依頼ユーザー')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name='グループ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='依頼日時')

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"
    
    class Meta:
        ordering = ["-created_at"]