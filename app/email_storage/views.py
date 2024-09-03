from django.shortcuts import render, redirect
from django.db.models import Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView
from .forms import EmailAccountForm
from .models import EmailAccount
from core.service.imap_client import AsyncEmailClient
from asgiref.sync import async_to_sync


class EmailAccountsView(ListView, LoginRequiredMixin):
    template_name = 'email_storage/email_accounts.html'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        return EmailAccount.objects.filter(user=user).prefetch_related('messages').annotate(count_messages=Count('messages')).order_by('-id')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = EmailAccountForm()
        return context

    def post(self, request, *args, **kwargs):
        form = EmailAccountForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            host = f'imap.{email.split("@")[1]}'
            login = async_to_sync(self.async_login)(email, password, host)
            if login:
                email_account, _ = EmailAccount.objects.get_or_create(
                    email=email,
                    password=password,
                    user=request.user,
                    defaults={
                        "host": host
                    }
                )
                if not _:
                    return JsonResponse({'detail': 'Аккаунт уже занят'}, status=400)
                return JsonResponse({'status': 'ok'})
            return JsonResponse({'detail': 'В доступе отказано. Проверте доступ и настройки почтового сервера'},
                                status=400)
        return JsonResponse({'detail': 'Заполните поля'}, status=400)

    async def async_login(self, email, password, host):
        async with AsyncEmailClient(host=host, ssl=True) as client:
            login = await client.login(email, password)
            return login


class EmailAccountDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'email_storage/email_account.html'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        pk = self.kwargs.get('pk')
        email_account = EmailAccount.objects.get(pk=pk, user=user).prefetch_related('messages')
        messages = email_account.messages.order_by('-date_sent')
        paginator = Paginator(messages, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        context['email_account'] = email_account
        context['messages'] = page_obj.object_list
        context['page_obj'] = page_obj
        return context
