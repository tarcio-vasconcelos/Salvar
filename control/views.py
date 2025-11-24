from django.shortcuts import render, get_object_or_404
from .models import Empenho, Categoria, ExercicioAnual, CategoriaExercicioOrcamento
from django.views.generic import ListView

# Create your views here.
class EmpenhoListView(ListView):
    model = Empenho
    template_name = 'control\control.html'
    context_object_name = 'empenhos'

    def get_queryset(self):
        queryset = super().get_queryset()
        exercicio_id = self.request.GET.get('exercicio')
        categoria_id = self.request.GET.get('categoria')

        if exercicio_id:
            queryset = queryset.filter(exercicio_anual__id=exercicio_id)
        
        if categoria_id:
            queryset = queryset.filter(categoria__id=categoria_id)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exercicio_id = self.request.GET.get('exercicio')
        categoria_id = self.request.GET.get('categoria')

        context['categorias'] = Categoria.objects.all()
        context['exercicios_anuais'] = ExercicioAnual.objects.all()

        context['categoria_selecionada_id'] = int(categoria_id) if categoria_id else None

        if exercicio_id:
            exercicio = get_object_or_404(ExercicioAnual, id=exercicio_id)
            context['exercicio_selecionado'] = exercicio
            
            if categoria_id:
                categoria = get_object_or_404(Categoria, id=categoria_id)
                context['categoria_selecionada'] = categoria
                
                # Cálculo de saldo e orçamento no nível Categoria/Exercício
                orcamento_categoria = get_object_or_404(
                    CategoriaExercicioOrcamento,
                    exercicio_anual=exercicio,
                    categoria=categoria
                )
                context['orcamento_categoria'] = orcamento_categoria
                context['saldo_disponivel_categoria'] = orcamento_categoria.get_saldo_disponivel_categoria()
                
            else:
                # Se apenas o exercício for selecionado, mostra o resumo do ano
                context['saldo_disponivel'] = exercicio.get_saldo_disponivel()
                context['orcamento_total'] = exercicio.get_orcamento_total_categorias()
                
                # Buscar e exibir os orçamentos por categoria para o exercício selecionado
                context['orcamentos_por_categoria'] = CategoriaExercicioOrcamento.objects.filter(exercicio_anual=exercicio).order_by('categoria__nome')

        return context