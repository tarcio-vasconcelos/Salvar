from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date

# Create your models here.
class Contrato(models.Model):
    STATUS_CHOICES = [
        ('ativo','Ativo'),
        ('concluído','Concluído'),
        ('cancelado','Cancelado'),
        ('secundário','Secundário')
        ]
    
    numero_contrato = models.CharField(max_length=50, unique=True, verbose_name='Número do contrato')
    nome_empresa = models.CharField(max_length=100, verbose_name="Nome da Empresa")
    objeto = models.TextField(verbose_name="Objeto do Contrato")
    sei = models.CharField(max_length=50, verbose_name="SEI")
    gestor_contrato = models.CharField(max_length=100, verbose_name="Gestor do Contrato")
    fiscal_contrato = models.CharField(max_length=100, verbose_name="Fiscal do Contrato")
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_termino = models.DateField(verbose_name="Data de Término")
    vigencia = models.IntegerField(verbose_name="Vigência (meses)")
    saldo_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Saldo Total"
    )
    secundario = models.BooleanField(verbose_name="Contrato secundário",default=False,help_text="Marque se o contrato é parte de um maior")
    maior = models.CharField(verbose_name="Contrato maior",blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ativo',
        verbose_name="Status do Contrato"
    )

    def __str__(self):
        return f"{self.numero_contrato} - {self.nome_empresa}"
    
    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ["-nome_empresa"]
    
    @property
    def saldo_utilizado(self):
        total_gasto = self.saldos_mensais.aggregate(
            total = models.Sum("valor_gasto"))["total"] or 0
        return round(total_gasto)
    
    @property
    def saldo_restante(self):
        return round(self.saldo_total - self.saldo_utilizado)
    
    @property
    def percentual_utilizado(self):
        if self.saldo_total > 0:
            return round((self.saldo_utilizado / self.saldo_total) * 100)
        return 0
    
    @property
    def dias_para_vencimento(self):
        hoje = date.today()
        if self.data_termino > hoje:
            return (self.data_termino - hoje).days
        return 0 

    @property
    def precisa_notificacao_saldo(self):
        if self.status == 'ativo':
            return self.percentual_utilizado >= 70
    
    @property
    def precisa_notificacao_vencimento(self):
        if self.status == 'ativo':
            return self.dias_para_vencimento <= 150 and self.dias_para_vencimento > 0
    
    def calcular_valor_mensal_fixo(self):
        if self.vigencia and self.vigencia > 0:
            return self.saldo_total / self.vigencia
        return Decimal('0.00')

class Saldo_mensal(models.Model):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name="saldos_mensais",
        verbose_name="Contrato"
    )
    mes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Mês"
    )
    ano = models.IntegerField(
        validators=[MinValueValidator(2000),MaxValueValidator(2099)],
        verbose_name="Ano"
    )
    valor_gasto = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Valor Gasto no Mês"
    )
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Saldo Mensal"
        verbose_name_plural = "Saldos Mensais"
        unique_together = ['contrato', 'mes', 'ano']
        ordering = ['-ano', '-mes']

    def __str__(self):
        return f"{self.contrato} - {self.mes}/{self.ano}"

    @property
    def data_referencia(self):
        return date(self.ano, self.mes, 1)