from django.shortcuts import render, get_object_or_404
from datetime import date, timedelta
from django.db.models import Q
from .models import Contrato
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator
import unicodedata
from django.db import models
from django.http import JsonResponse
from decimal import Decimal
from django.core.mail import send_mail

# Create your views here.
def home(request):
    contratos = Contrato.objects.all()
    contratos_com_alerta = contratos.filter(
        Q(status='ativo') & (
        Q(saldos_mensais__isnull=False) &
        Q(email=False) |
        Q(data_termino__lte=date.today() + timedelta(days=150)) &
        Q(email=False)
        )
    )
    if contratos_com_alerta:
        for contrato in contratos_com_alerta:
            send_mail(
                f"Contrato {contrato.numero_contrato} em alerta!",
                f"O {contrato.numero_contrato} da empresa {contrato.nome_empresa} precisa de atenção!",
                None,
                ["seplag.uadtg@gmail.com"],
            )
    return render(request,'contract/index.html')

def dashboard(request):
    contratos = Contrato.objects.all()
    pre_total_contratos = contratos.filter(Q(status = 'ativo'))
    total_contratos = pre_total_contratos.count()
    contratos_com_alerta = contratos.filter(
        Q(status='ativo') & (
        Q(saldos_mensais__isnull=False) |
        Q(data_termino__lte=date.today() + timedelta(days=150))
    )
    ).distinct()
    
    context = {
        'total_contratos': total_contratos,
        'contratos_com_alerta': contratos_com_alerta.count(),
        'contratos_recentes': contratos[:5],
        'notificacoes': []
    }
    
    # Adicionar notificações
    for contrato in contratos:
        if contrato.precisa_notificacao_saldo:
            context['notificacoes'].append({
                'contrato': contrato,
                'tipo': 'saldo',
                'mensagem': f'Saldo baixo: {contrato.percentual_utilizado:.1f}% utilizado'
            })
        if contrato.precisa_notificacao_vencimento:
            context['notificacoes'].append({
                'contrato': contrato,
                'tipo': 'vencimento',
                'mensagem': f'Vence em {contrato.dias_para_vencimento} dias'
            })
    
    return render(request, 'contract/dashboard.html', context)

class ContratoList(ListView):
    model = Contrato
    template_name = 'contract\contract_list.html'
    context_object_name = 'contratos'
    paginate_by = 10

    def get_queryset(self):
        queryset = Contrato.objects.all().order_by('nome_empresa')
        search = self.request.GET.get('search')
        if search:
            if search.lower() == 'venc':
                queryset = queryset.filter(self.q_precisa_notificacao())
                return queryset
            if search.lower() == 'vig':
                search = 'ativo'
            if search.lower() == 'saldo':
                search = '1'
                queryset = queryset.filter(self.precisa_notificacao_saldo
                )
            if search.lower() == '':
                return queryset
            form = unicodedata.normalize('NFKD', search)
            search1 = "".join([c for c in form if not unicodedata.combining(c)])
            queryset = queryset.filter(
                Q(numero_contrato__icontains=search or search1)|
                Q(nome_empresa__icontains=search or search1) |
                Q(objeto__icontains=search or search1) |
                Q(gestor_contrato__icontains=search or search1) |
                Q(fiscal_contrato__icontains=search or search1) |
                Q(status__icontains=search or search1)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context
    
    def lista_produtos(request):
        search = request.GET.get('search')
        produtos = Contrato.objects.all()

        if search:
            produtos = produtos.filter(nome__icontains=search)

        paginator = Paginator(produtos, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'search': search,
        }

        return render(request, 'contract/contract_list.html', context)

def metrics(request):
    contratos_por_gestor = Contrato.objects.filter(status="ativo").values(
        'gestor_contrato'
    ).annotate(count=models.Count('id')).order_by('-count')

    contratos_por_fiscal = Contrato.objects.filter(status="ativo").values(
        'fiscal_contrato'
    ).annotate(count=models.Count('id')).order_by('-count')

    contratos_vencimento_proximo = Contrato.objects.filter(
        data_termino__lte=date.today() + timedelta(days=150),
        data_termino__gt=date.today(),
        status='ativo'
    ).count()

    contratos_normais = Contrato.objects.filter(
        secundario=False
    ).count()

    contratos_ativos = Contrato.objects.filter(
        status='ativo',
        secundario=False
    ).count()

    contratos_baixo_saldo = 0
    for contrato in Contrato.objects.filter(status='ativo'):
        if contrato.precisa_notificacao_saldo:
            contratos_baixo_saldo += 1

    context = {
        'contratos_por_gestor': contratos_por_gestor,
        'contratos_por_fiscal': contratos_por_fiscal,
        'contratos_vencimento_proximo': contratos_vencimento_proximo,
        'contratos_baixo_saldo': contratos_baixo_saldo,
        'contratos_normais': contratos_normais,
        'contratos_ativos': contratos_ativos
    }

    return render(request, 'contract/metrics.html', context)

class ContractDetail(DetailView):
    model = Contrato
    template_name = 'contract\contract_detail.html'
    context_object_name = 'contrato'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contrato = self.get_object()
        context['saldos_mensais'] = contrato.saldos_mensais.all()
        context['notificacoes'] = []
        
        if contrato.precisa_notificacao_saldo:
            context['notificacoes'].append({
                'tipo': 'warning',
                'mensagem': f'Atenção: Saldo utilizado está em {contrato.percentual_utilizado:.1f}% (acima de 70%)'
            })
        
        if contrato.precisa_notificacao_vencimento:
            context['notificacoes'].append({
                'tipo': 'danger',
                'mensagem': f'Atenção: Contrato vence em {contrato.dias_para_vencimento} dias'
            })
        
        return context
    
def graphy(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    
    context = {
        'contrato': contrato,
        'saldos_mensais': contrato.saldos_mensais.all().order_by('ano', 'mes')
    }
    
    return render(request, 'contract\graphy.html', context)

def evolution(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    saldos = contrato.saldos_mensais.all().order_by('ano', 'mes')
    
    labels = []
    dados_gastos = []
    dados_saldo_restante = []
    saldo_acumulado = 0
    
    for saldo in saldos:
        labels.append(f"{saldo.mes:02d}/{saldo.ano}")
        saldo_acumulado += float(saldo.valor_gasto)
        dados_gastos.append(saldo_acumulado)
        dados_saldo_restante.append(float(contrato.saldo_total) - saldo_acumulado)
    
    data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Saldo Utilizado',
                'data': dados_gastos,
                'borderColor': 'rgb(255, 99, 132)',
                'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                'tension': 0.1
            },
            {
                'label': 'Saldo Restante',
                'data': dados_saldo_restante,
                'borderColor': 'rgb(54, 162, 235)',
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'tension': 0.1
            }
        ]
    }
    
    return JsonResponse(data)

def monthly_expenses(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    saldos = contrato.saldos_mensais.all().order_by('ano', 'mes')

    labels = []
    acima_media = []
    abaixo_media = []

    valor_mensal_fixo = Decimal(contrato.calcular_valor_mensal_fixo)

    for saldo in saldos:
        labels.append(f"{saldo.mes:02d}/{saldo.ano}")

        if saldo.valor_gasto > valor_mensal_fixo:
            acima_media.append(float(saldo.valor_gasto))
            abaixo_media.append(None)
        else:
            acima_media.append(None)
            abaixo_media.append(float(saldo.valor_gasto))

    if not saldos:
        today = date.today()
        labels.append(f"{today.month:02d}/{today.year}")
        acima_media.append(0)
        abaixo_media.append(0)

    linha_media = [float(valor_mensal_fixo)] * len(labels)

    data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Gastos Acima da Média',
                'data': acima_media,
                'backgroundColor': 'rgba(255, 99, 132, 0.8)',
                'borderColor': 'rgba(255, 99, 132, 1)',
                'type': 'bar'
            },
            {
                'label': 'Gastos Abaixo da Média',
                'data': abaixo_media,
                'backgroundColor': 'rgba(54, 162, 235, 0.8)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'type': 'bar'
            },
            {
                'label': 'Valor Mensal Fixo',
                'data': linha_media,
                'borderColor': 'rgb(252, 41, 0)',
                'backgroundColor': 'rgba(252, 41, 0)',
                'type': 'line',
                'fill': False,
                'spanGaps': True,
                'tension': 0
            }
        ]
    }

    return JsonResponse(data)

def balance(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    
    saldo_utilizado = float(contrato.saldo_utilizado)
    saldo_restante = float(contrato.saldo_restante)
    
    data = {
        'labels': ['Saldo Utilizado', 'Saldo Restante'],
        'datasets': [{
            'data': [saldo_utilizado, saldo_restante],
            'backgroundColor': [
                'rgba(255, 99, 132, 0.8)',
                'rgba(54, 162, 235, 0.8)'
            ],
            'borderColor': [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)'
            ],
            'borderWidth': 1
        }]
    }
    
    return JsonResponse(data)