from django.contrib.auth.forms import UserCreationForm
from django import forms
from accounts.models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15)
    department = forms.CharField(max_length=100)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone', 'department', 'password1', 'password2')