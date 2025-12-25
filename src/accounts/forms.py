from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator


class CustomUserCreationForm(UserCreationForm):
    custom_user_id = forms.CharField(
        label="ID",
        max_length=15,
        required=True,
        validators=[
            RegexValidator(
                regex=r"^[0-9A-Za-z]+$",
                message="IDは半角英数字のみで入力してください。",
                code="invalid_custom_user_id",
            )
        ],
        error_messages={
            "required": "IDを入力してください。",
            "max_length": "IDは15文字以内で入力してください。",
        },
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
        validators=[
            RegexValidator(
                # 英字を1文字以上 & 数字を1文字以上含む
                regex=r"^(?=.*[A-Za-z])(?=.*\d).+$",
                message="パスワードは英字と数字をそれぞれ1文字以上含めてください。",
                code="invalid_password_format",
            )
        ],
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                # min_lengthはsettings.pyにて定義済
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

    def save(self, commit=True):
        """
        UserCreationForm の save は標準の password しかセットしないため、
        CustomUser の必須フィールド（password1/password2/question/answer）も埋める。
        """
        user = super().save(commit=False)
        user.custom_user_id = self.cleaned_data["custom_user_id"]
        user.question = self.cleaned_data["question"]
        user.answer = self.cleaned_data["answer"]
        user.password1 = self.cleaned_data["password1"]
        user.password2 = self.cleaned_data["password2"]

        if commit:
            user.save()
        return user
