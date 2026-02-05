from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls), #admin
    path('', include('contract.urls')), #Contract
    path('control/', include('control.urls')),
    path('laws/', include('laws.urls')) # Laws
]