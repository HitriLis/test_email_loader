from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm


class SignInForm(AuthenticationForm):
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages['invalid_login'] = "Неправильно указана почта пользователя или пароль."

        for field in self.fields:
            self.fields[field].label_suffix = ""
            self.fields[field].widget.attrs['class'] = 'form-control'







