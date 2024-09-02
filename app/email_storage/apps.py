from django.apps import AppConfig


class EmailStorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'email_storage'
    verbose_name = "Email storage"
