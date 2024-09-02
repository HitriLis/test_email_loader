from datetime import datetime

from channels.db import database_sync_to_async
from django.db import models
from django.core.files.base import ContentFile
from users.models import User


class EmailAccount(models.Model):
    email = models.EmailField(db_index=True, verbose_name='Почта')
    password = models.CharField(max_length=254, null=True, blank=True, verbose_name='Пароль')
    host = models.CharField(max_length=254, null=True, blank=True, verbose_name='Хост')
    last_parse = models.DateTimeField(blank=True, null=True)
    start_parse = models.BooleanField(default=False)
    message_action = models.CharField(max_length=20, choices=[
        ('MESSAGE_LOAD', 'Messages load'),
        ('MESSAGE_SEARCH', 'Messages search')
    ], blank=True, null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='email_account'
    )

    class Meta:
        verbose_name = "Email аккаунт"
        verbose_name_plural = "Email аккаунты"

    @classmethod
    @database_sync_to_async
    def get_email_account(cls, email_account_id, user_id):
        return cls.objects.filter(
            pk=email_account_id,
            user_id=user_id
        ).annotate(count_messages=models.Count('messages')).first()

    @classmethod
    @database_sync_to_async
    def get_last_message(cls):
        return cls.messages.order_by('-date_sent').first()


class EmailMessage(models.Model):
    uid = models.CharField(max_length=100, blank=True, null=True)
    subject = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    date_sent = models.DateTimeField(blank=True, null=True)
    date_received = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_big_text = models.BooleanField(default=False)
    account = models.ForeignKey(
        EmailAccount,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='messages'
    )

    class Meta:
        verbose_name = "Email сообщене"
        verbose_name_plural = "Email сообщения"

    @classmethod
    @database_sync_to_async
    def get_last_message(cls, email_account_id: int):
        return cls.objects.filter(account_id=email_account_id).order_by('-date_sent').first()

    @classmethod
    @database_sync_to_async
    def exists_lasts_messages(cls, email_account_id: int, date_sent: datetime = None):
        return list(cls.objects.filter(
            account_id=email_account_id, date_sent__date=date_sent.date()).values_list('uid', flat=True))

    @classmethod
    @database_sync_to_async
    def email_messages_create(cls, messages_model_list: list):
        return cls.objects.bulk_create(messages_model_list)


class EmailFile(models.Model):
    file = models.FileField(upload_to='attachments/', blank=True, null=True)
    message_uid = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Фаийл"
        verbose_name_plural = "Фаийлы"

    @classmethod
    @database_sync_to_async
    def email_files_create(cls, files_list: list):
        for file in files_list:
            try:
                model_file = cls(
                    message_uid=file.uid
                )
                model_file.file.save(file.filename, ContentFile(file.attachment), save=True)
            except Exception as e:
                print(e)
