from django import forms


class EmailAccountForm(forms.Form):
    email = forms.EmailField(label="Почта", max_length=100)
    password = forms.CharField(label="Пароль", max_length=100)
