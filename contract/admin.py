from django.contrib import admin
from .models import Contrato, Saldo_mensal
from django.contrib.auth.models import User, Group

# Register your models here.
admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.register(Contrato)

admin.site.register(Saldo_mensal)