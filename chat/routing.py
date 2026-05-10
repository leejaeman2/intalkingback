from django.urls import path
from chat.consumers import CallConsumer

websocket_urlpatterns = [
  path('ws/call/', CallConsumer.as_asgi()),
]
