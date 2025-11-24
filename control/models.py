from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

# Create your models here.
class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    
    class Meta:
        verbose_name = "Categoria de Empenho"
        verbose_name_plural = "Categorias de Empenho"
    
    def __str__(self):
        return self.nome

class ExercicioAnual(models.Model):
    ano = models.IntegerField(unique=True, verbose_name="Ano do Exercício")
    valor_orcamento = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor do Orçamento Anual")

    class Meta:
        verbose_name = "Exercício Anual"
        verbose_name_plural = "Exercícios Anuais"

    def get_saldo_disponivel(self):
        saldo_categorias = sum(
            ceo.get_saldo_disponivel_categoria() 
            for ceo in self.categoriaexercicioorcamento_set.all()
        )
        return saldo_categorias

    def __str__(self):
        return f"Exercício {self.ano}"
    
    def get_orcamento_total_categorias(self):
        return sum(
            ceo.valor_orcamento_categoria 
            for ceo in self.categoriaexercicioorcamento_set.all()
        )
    
class CategoriaExercicioOrcamento(models.Model):
    exercicio_anual = models.ForeignKey(ExercicioAnual, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    valor_orcamento_categoria = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Orçamento da Categoria")
       
    class Meta:
        verbose_name = "Exercício Anual por Categoria"
        verbose_name_plural = "Exercícios Anuais por Categoria"

    def __str__(self):
        return f"Exercício {self.ano}"
    
    def get_saldo_disponivel_categoria(self):
        empenhos_da_categoria = Empenho.objects.filter(
            exercicio_anual=self.exercicio_anual,
            categoria=self.categoria
        ).aggregate(total_empenhado=models.Sum("valor"))["total_empenhado"] or 0
        return self.valor_orcamento_categoria - empenhos_da_categoria

    def get_saldo_percentual_disponivel(self):
        saldo_disponivel = self.get_saldo_disponivel_categoria()
        if self.valor_orcamento_categoria and self.valor_orcamento_categoria > 0:
            return (saldo_disponivel / self.valor_orcamento_categoria) * 100
        return 0
    
    def save(self, *args, **kwargs):
        self.valor_orcamento_categoria = self.exercicio_anual.valor_orcamento
        super().save(*args, **kwargs)

class Empenho(models.Model):
    exercicio_anual = models.ForeignKey(ExercicioAnual, on_delete=models.CASCADE, verbose_name="Exercício Anual")
    numero_empenho = models.CharField(max_length=255, blank=True, null=True, verbose_name="Número do Empenho")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoria")
    valor = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor do Empenho")
    data_empenho = models.DateField(default=timezone.now, verbose_name="Data do Empenho")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    codigo_orcamentario = models.CharField(max_length=255, blank=True, null=True, verbose_name="Código Orçamentário")

    class Meta:
        verbose_name = "Empenho"
        verbose_name_plural = "Empenhos"
        unique_together = ('numero_empenho', 'exercicio_anual')

    def __str__(self):
        return f"Empenho {self.numero_empenho} ({self.exercicio_anual.ano})"

    def clean(self):
        super().clean()
        if self.valor <= 0:
            raise ValidationError({"valor": "O valor do empenho deve ser maior que zero."})

        if self.categoria:
            try:
                orcamento_categoria = CategoriaExercicioOrcamento.objects.get(
                    exercicio_anual=self.exercicio_anual,
                    categoria=self.categoria
                )
                saldo_atual = orcamento_categoria.get_saldo_disponivel_categoria()
                
                valor_antigo = 0
                if self.pk:
                    valor_antigo = Empenho.objects.get(pk=self.pk).valor
                
                saldo_apos_edicao = saldo_atual + valor_antigo
                
                if self.valor > saldo_apos_edicao:
                    raise ValidationError({
                        "valor": f"O valor do empenho (R$ {self.valor}) excede o saldo disponível para a categoria '{self.categoria.nome}' no exercício {self.exercicio_anual.ano}. Saldo disponível: R$ {saldo_apos_edicao:.2f}"
                    })

            except CategoriaExercicioOrcamento.DoesNotExist:
                ceo, created = CategoriaExercicioOrcamento.objects.get_or_create(
                    exercicio_anual=self.exercicio_anual,
                    categoria=self.categoria,
                    defaults={'valor_orcamento_categoria': self.exercicio_anual.valor_orcamento}
                )
                saldo_atual = ceo.get_saldo_disponivel_categoria()
                
                if self.valor > saldo_atual:
                     raise ValidationError({
                        "valor": f"O valor do empenho (R$ {self.valor}) excede o saldo disponível para a categoria '{self.categoria.nome}' no exercício {self.exercicio_anual.ano}. Saldo disponível: R$ {saldo_atual:.2f}"
                    })


    def save(self, *args, **kwargs):
        self.full_clean()

        if not self.pk:
            ano = self.exercicio_anual.ano
            ultimo_empenho = Empenho.objects.filter(
                exercicio_anual=self.exercicio_anual
            ).order_by('-numero_empenho').first()
            
            if ultimo_empenho and ultimo_empenho.numero_empenho:
                try:
                    ultimo_numero = int(ultimo_empenho.numero_empenho.split('/')[0])
                except ValueError:
                    ultimo_numero = 0
            else:
                ultimo_numero = 0
                
            proximo_numero = ultimo_numero + 1

            self.numero_empenho = f"{proximo_numero:03d}/{ano}"

        super().save(*args, **kwargs)

        if self.categoria:
            CategoriaExercicioOrcamento.objects.get_or_create(
                exercicio_anual=self.exercicio_anual,
                categoria=self.categoria,
                defaults={'valor_orcamento_categoria': self.exercicio_anual.valor_orcamento}
            )