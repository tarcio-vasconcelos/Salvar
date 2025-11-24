from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.laws_list, name='laws_list'),
]