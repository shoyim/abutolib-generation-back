from django.urls import path
from .views import QuizGenerateView

urlpatterns = [
    path('generate/', QuizGenerateView.as_view()),
]