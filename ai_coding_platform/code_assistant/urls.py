from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('run_code/', views.run_code, name='run_code'),
    path('assistant_feedback/', views.assistant_feedback, name='assistant_feedback'),
    path('learning_resources/', views.learning_resources, name='learning_resources'),
    path('get_question/', views.get_question, name='get_question'),
]
