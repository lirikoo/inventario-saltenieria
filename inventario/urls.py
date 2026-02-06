from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='inventario/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('sucursales/', views.seleccionar_sucursal, name='seleccion_sucursal'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('guardar/', views.guardar_registro, name='guardar_registro'),
    path('descargar-pdf/', views.generar_pdf_estilo_cuaderno, name='descargar_pdf'),
    path('historial/', views.historial_ventas, name='historial_ventas'),
    path('descargar-pdf/', views.generar_pdf_estilo_cuaderno, name='generar_pdf'),
    path('ver-planilla/', views.ver_planilla_html, name='ver_planilla'),

]
