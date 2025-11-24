from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), #Tela inicial
    path('contract/dashboard', views.dashboard, name='dashboard_contract'), #Dashboard
    path('contract/list', views.ContratoList.as_view(), name='contract_list'), # List
    path('contract/metrics', views.metrics, name='metrics'), #metrics
    path('contract/<int:pk>/detail', views.ContractDetail.as_view(), name='detalhe'), #Detail

    #Charts
    path('contract/<int:pk>/graphy', views.graphy, name='graphy'),
    path('contract/<int:pk>/monthly_expenses', views.monthly_expenses, name='monthly_expenses'),
    path('contract/<int:pk>/balance', views.balance, name='balance'),
    path('contract/<int:pk>/evolution', views.evolution, name='evolution'),
]