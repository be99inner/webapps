from django import forms
from django.contrib.auth import ( authenticate, get_user_model, login, logout, )


class UserLoginForm(forms.Form):
    username = forms.CharField();
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self, *args, **kwargs):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError("Username or Password is not correct!")
            return super(UserLoginForm,self).clean(*args, **kwargs)
