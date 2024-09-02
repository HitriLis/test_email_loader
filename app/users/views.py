from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from .forms import SignInForm


def index(request):
    return redirect('home')

class SignInView(LoginView):
    template_name = 'users/login.html'
    form_class = SignInForm
    success_url = reverse_lazy('accounts')

    def get_success_url(self):
        return self.success_url

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        return HttpResponseRedirect(self.get_success_url())


class SignOutView(LogoutView):
    next_page = reverse_lazy('login')