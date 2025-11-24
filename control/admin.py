from django.contrib import admin
from .models import Categoria, ExercicioAnual, CategoriaExercicioOrcamento, Empenho
# Register your models here.
admin.site.register(Categoria)

admin.site.register(ExercicioAnual)

admin.site.register(Empenho)