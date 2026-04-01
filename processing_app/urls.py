from django.urls import path
from .views import TextChunkingView

urlpatterns = [
    path('chunk/', TextChunkingView.as_view(), name='text_chunking'),
]