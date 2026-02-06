from django.contrib import admin
from .models import Categoria, Producto, RegistroDiario, CajaDiaria, Gasto, Sucursal


admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(RegistroDiario)
admin.site.register(CajaDiaria)
admin.site.register(Gasto)
admin.site.register(Sucursal)