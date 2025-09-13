from django import forms

from accounts.models import CustomUser

from .models import Group, Post


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name"]


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["product_name", "customer_category", "contents", "group", "image"]
        widgets = {
            "product_name": forms.TextInput(attrs={"class": "form-control"}),
            "customer_category": forms.TextInput(attrs={"class": "form-control"}),
            "contents": forms.Textarea(attrs={"class": "form-control"}),
            "group": forms.Select(attrs={"class": "form-control"}),
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }
        labels = {
            "product_name": "商品名",
            "customer_category": "業態",
            "contents": "内容",
            "group": "グループ",
            "image": "画像",
        }
        help_texts = {
            "product_name": "商品名を入力してください。",
            "customer_category": "業態を入力してください。",
            "contents": "投稿内容を入力してください。",
            "group": "グループを選択してください。",
            "image": "画像を選択してください。",
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("画像サイズは5MB以下にしてください。")

            allowed_types = ["image/jpeg", "image/png", "image/gif"]
            if (
                hasattr(image, "content_type")
                and image.content_type not in allowed_types
            ):
                raise forms.ValidationError(
                    "サポートされている画像形式はJPEG, PNG, GIFのみです。"
                )

        return image

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(PostForm, self).__init__(*args, **kwargs)
        if user:
            user_groups = Group.objects.filter(users=user)
            print(f"User Groups: {user_groups}")
            self.fields["group"].queryset = user_groups


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["username", "profile_image"]
