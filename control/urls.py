from django.urls import path
from . import views

urlpatterns = [
    path('', views.EmpenhoListView.as_view(), name='control_list'),
]
