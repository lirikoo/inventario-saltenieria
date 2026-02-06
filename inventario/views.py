from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Producto, RegistroDiario, Sucursal, CajaDiaria, Gasto, Categoria
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

# Importación de WeasyPrint
from weasyprint import HTML

@login_required
def seleccionar_sucursal(request):
    sucursales = Sucursal.objects.all()
    return render(request, 'inventario/seleccion_sucursal.html', {'sucursales': sucursales})

@login_required
def lista_productos(request):
    sucursal_id = request.GET.get('sucursal_id')
    if not sucursal_id:
        return redirect('seleccion_sucursal')
    suc_obj = get_object_or_404(Sucursal, id=sucursal_id)
    productos = Producto.objects.filter(sucursal=suc_obj).order_by('categoria')
    return render(request, 'inventario/lista.html', {
        'productos': productos, 
        'sucursal_activa': suc_obj
    })

@login_required
def guardar_registro(request):
    if request.method == "POST":
        sucursal_id = request.POST.get('sucursal_id')
        suc_obj = get_object_or_404(Sucursal, id=sucursal_id)
        
        # 1. Crear el cierre de caja
        caja = CajaDiaria.objects.create(
            sucursal=suc_obj,
            efectivo=float(request.POST.get('caja_efectivo') or 0),
            qr=float(request.POST.get('caja_qr') or 0),
            tarjetero=float(request.POST.get('caja_tarjeta') or 0)
        )

        # 2. Guardar cada fila de producto
        productos = Producto.objects.filter(sucursal=suc_obj)
        for p in productos:
            p_v = request.POST.get(f'p_{p.id}', 0)
            e_v = request.POST.get(f'e_{p.id}', 0)
            b_v = request.POST.get(f'b_{p.id}', 0)
            t_v = request.POST.get(f't_cant_{p.id}', 0)
            s_v = request.POST.get(f's_{p.id}', 0)
            
            if any(int(v or 0) > 0 for v in [p_v, e_v, b_v, t_v, s_v]):
                RegistroDiario.objects.create(
                    producto=p,
                    sucursal=suc_obj,
                    produccion=int(p_v or 0),
                    entrada=int(e_v or 0),
                    baja=int(b_v or 0),
                    traspaso=int(t_v or 0),
                    salida=int(s_v or 0)
                )

        return JsonResponse({"status": "success", "caja_id": caja.id})

@login_required
def historial_ventas(request):
    """Esta función evita el error AttributeError en la terminal"""
    cierres = CajaDiaria.objects.all().order_by('-fecha', '-id')
    return render(request, 'inventario/historial.html', {'cierres': cierres})

@login_required
def generar_pdf_estilo_cuaderno(request):
    caja_id = request.GET.get('caja_id')
    cierre = get_object_or_404(CajaDiaria, id=caja_id)
    
    # 1. Obtener TODOS los productos de esta sucursal específica
    # Los ordenamos por categoría para que la tabla sea legible
    productos_sucursal = Producto.objects.filter(
        sucursal=cierre.sucursal
    ).select_related('categoria').order_by('categoria__nombre', 'nombre')

    # 2. Obtener los registros que SÍ tienen datos para este día
    registros_existentes = {
        r.producto_id: r 
        for r in RegistroDiario.objects.filter(
            sucursal=cierre.sucursal, 
            fecha_creacion__date=cierre.fecha
        )
    }

    # 3. Construir la lista "maestra" para la tabla y calcular totales
    filas_tabla = []
    total_ventas_bs = 0
    
    for p in productos_sucursal:
        reg = registros_existentes.get(p.id) # Buscamos si el producto tiene registro hoy
        
        # Si hay registro, sumamos a la venta esperada
        if reg:
            total_ventas_bs += (reg.salida * p.precio_unitario)
            
        filas_tabla.append({
            'producto': p,
            'reg': reg  # Si no hay registro, esto será None
        })
    
    # 4. Cálculos finales de caja
    total_caja_real = cierre.efectivo + cierre.qr + cierre.tarjetero
    diferencia = total_caja_real - total_ventas_bs

    # 5. Renderizar el HTML con la nueva lista 'filas'
    html_string = render_to_string('inventario/pdf_template.html', {
        'cierre': cierre,
        'filas': filas_tabla, # <--- Usamos esta nueva lista
        'total_ventas': total_ventas_bs,
        'total_caja': total_caja_real,
        'diferencia': diferencia,
        'fecha_emision': timezone.now(),
    })

    # Crear el PDF con WeasyPrint
    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Reporte_{cierre.sucursal.nombre}_{cierre.fecha}.pdf"'
    return response

@login_required
def ver_planilla_html(request):
    caja_id = request.GET.get('caja_id')
    cierre = get_object_or_404(CajaDiaria, id=caja_id)
    
    # 1. Obtener productos y registros (Misma lógica que el PDF)
    productos_sucursal = Producto.objects.filter(sucursal=cierre.sucursal).select_related('categoria').order_by('categoria__nombre', 'nombre')
    registros_existentes = {r.producto_id: r for r in RegistroDiario.objects.filter(sucursal=cierre.sucursal, fecha_creacion__date=cierre.fecha)}

    filas_tabla = []
    total_ventas_bs = 0
    for p in productos_sucursal:
        reg = registros_existentes.get(p.id)
        if reg:
            total_ventas_bs += (reg.salida * p.precio_unitario)
        filas_tabla.append({'producto': p, 'reg': reg})
    
    total_caja_real = cierre.efectivo + cierre.qr + cierre.tarjetero
    diferencia = total_caja_real - total_ventas_bs

    # 2. Renderizamos como una página WEB normal, no como PDF
    return render(request, 'inventario/pdf_template.html', {
        'cierre': cierre,
        'filas': filas_tabla,
        'total_ventas': total_ventas_bs,
        'total_caja': total_caja_real,
        'diferencia': diferencia,
        'fecha_emision': timezone.now(),
        'es_vista_web': True # Usaremos esto para ocultar cosas si es necesario
    })