from django.urls import path
from .views import EmailAccountsView, EmailAccountDetailView

urlpatterns = [
    path("accounts/", EmailAccountsView.as_view(), name='accounts'),
    path("accounts/<int:pk>/", EmailAccountDetailView.as_view(), name='email_account_detail'),
]
