from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    custom_user_id = forms.CharField(max_length=30, required=True)
    
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'custom_user_id', 'password1', 'password2', 'question', 'answer',)