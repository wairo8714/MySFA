from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class CustomUserCreationForm(UserCreationForm):
    custom_user_id = forms.CharField(
        label="ID",
        max_length=15,
        required=True,
    )
    
    question = forms.CharField(
        label="質問",
        max_length=20,
        required=True,
    )
    
    answer = forms.CharField(
        label="質問の答え",
        max_length=20, 
        required=True,
    )

    password1 = forms.CharField(
        label="パスワード",
        strip=False,
        max_length=20,
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                #min_lengthはsettings.pyにて定義済
                "maxlength": "20",
            }
        ),
        help_text="5〜20文字で入力してください。",
        error_messages={
            "max_length": "パスワードは20文字以内で入力してください。",
            "required": "パスワードを入力してください。",
        },
    )

    password2 = forms.CharField(
        label="Password confirmation",
        strip=False,
        max_length=20,
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "maxlength": "20",
            }
        ),
        help_text="確認のため、同じパスワードをもう一度入力してください。",
        error_messages={
            "max_length": "パスワード（確認）は20文字以内で入力してください。",
            "required": "確認用パスワードを入力してください。",
        },
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = (
            "username",
            "custom_user_id",
            "password1",
            "password2",
            "question",
            "answer",
        )
