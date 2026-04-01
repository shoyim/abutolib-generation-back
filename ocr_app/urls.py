from django.urls import path
from .views import OCRSimpleView

urlpatterns = [
    path('process/', OCRSimpleView.as_view(), name='ocr_simple'),
]