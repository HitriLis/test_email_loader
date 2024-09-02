from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/general/', consumers.GeneralConsumer.as_asgi()),
]
