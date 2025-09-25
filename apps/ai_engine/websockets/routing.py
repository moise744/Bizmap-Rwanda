# apps/ai_engine/websockets/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ai/chat/(?P<user_id>[^/]+)/', consumers.AIConversationConsumer.as_asgi()),
]