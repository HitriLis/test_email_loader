from django.urls import path
from .views import SignInView, SignOutView, index

urlpatterns = [
    path('', index, name='index'),
    path("login/", SignInView.as_view(), name='login'),
    path("sign-out/", SignOutView.as_view(), name='sign-out'),
]
