from django.urls import path
from .views import FullQuizGenerateView

urlpatterns = [
    path('generate/', FullQuizGenerateView.as_view()),
]