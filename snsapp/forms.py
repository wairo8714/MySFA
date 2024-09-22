from django import forms
from .models import Group, Post
from accounts.models import CustomUser

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']  # グループ名のみを入力させる

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['product_name', 'customer_category', 'contents', 'group']
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_category': forms.TextInput(attrs={'class': 'form-control'}),
            'contents': forms.Textarea(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'product_name': '商品名',
            'customer_category': '業態',
            'contents': '内容',
            'group': 'グループ',
        }
        help_texts = {
            'product_name': '商品名を入力してください。',
            'customer_category': '業態を入力してください。',
            'contents': '投稿内容を入力してください。',
            'group': 'グループを選択してください。',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PostForm, self).__init__(*args, **kwargs)
        if user:
            user_groups = Group.objects.filter(users=user)
            print(f"User Groups: {user_groups}")  # デバッグプリント
            self.fields['group'].queryset = user_groups  # ユーザーが参加しているグループのみを表示

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'profile_image']