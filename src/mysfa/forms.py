from django import forms

from accounts.models import CustomUser

from .models import Group, Post, ProductMaster, IndustryMaster


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name"]

class ProductMasterForm(forms.ModelForm):
    class Meta:
        model = ProductMaster
        fields = [
            "product_code",
            "name",
            "category_main",
            "category_sub",
            "custom_text_1",
            "custom_text_2",
            "custom_text_3",
            "custom_int_1",
            "custom_int_2",
            "custom_date_1",
            "description",
        ]


class IndustryMasterForm(forms.ModelForm):
    class Meta:
        model = IndustryMaster
        fields = ["name"]

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["group", "product", "industry", "status", "contents", "image"]
        widgets = {
            "group": forms.Select(attrs={"class": "form-control"}),
            "product": forms.Select(attrs={"class": "form-control"}),
            "industry": forms.Select(attrs={"class": "form-control"}),
            "status": forms.RadioSelect(),
            "contents": forms.Textarea(attrs={"class": "form-control"}),
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }
        labels = {
            "group": "グループ",
            "product": "商品",
            "industry": "業態",
            "status": "ステータス",
            "contents": "内容",
            "image": "画像",
        }
        help_texts = {
            "group": "投稿先グループを選択してください。",
            "product": "商品を選択してください。",
            "industry": "業態を選択してください。",
            "status": "営業状況を選択してください。",
            "contents": "投稿内容を入力してください。",
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
            self.fields["group"].queryset = Group.objects.filter(users=user, is_active=True)

        # グループ未選択の間は商品/業態を選べないようにする
        group = None
        if self.is_bound:
            raw = self.data.get("group")
            if raw:
                try:
                    group = Group.objects.filter(pk=raw).first()
                except (TypeError, ValueError):
                    group = None
        elif getattr(self.instance, "group_id", None):
            group = self.instance.group
        elif self.initial.get("group"):
            raw = self.initial.get("group")
            try:
                group = Group.objects.filter(pk=raw).first()
            except (TypeError, ValueError):
                group = None

        if group:
            self.fields["product"].queryset = ProductMaster.objects.filter(
                group=group, is_active=True
            ).order_by("product_code")
            self.fields["industry"].queryset = IndustryMaster.objects.filter(
                group=group, is_active=True
            ).order_by("name", "id")
            self.fields["product"].disabled = False
            self.fields["industry"].disabled = False
        else:
            self.fields["product"].queryset = ProductMaster.objects.none()
            self.fields["industry"].queryset = IndustryMaster.objects.none()
            self.fields["product"].disabled = True
            self.fields["industry"].disabled = True

        self.fields["group"].required = True
        self.fields["product"].required = True
        self.fields["industry"].required = True
        self.fields["status"].required = True


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["username", "profile_image"]
