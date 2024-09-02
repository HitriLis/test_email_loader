from django.contrib import admin
from email_storage.models import EmailAccount, EmailMessage, EmailFile


class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ["id"]
    model = EmailAccount


admin.site.register(EmailAccount, EmailAccountAdmin)


class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "uid", "subject"]
    model = EmailMessage


admin.site.register(EmailMessage, EmailMessageAdmin)


class EmailFileAdmin(admin.ModelAdmin):
    list_display = ["id"]
    model = EmailFile


admin.site.register(EmailFile, EmailFileAdmin)
