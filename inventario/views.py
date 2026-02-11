from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Sum, Case, When, Value, IntegerField

# Importación de modelos
from .models import (
    Producto, RegistroDiario, Sucursal, 
    CajaDiaria, Gasto, VentaSalteña, GastoExtra, Categoria
)

# Importación de WeasyPrint para los reportes
from weasyprint import HTML

# --- 1. NAVEGACIÓN ---

@login_required
def seleccionar_sucursal(request):
    """Muestra las sucursales disponibles para trabajar."""
    sucursales = Sucursal.objects.all()
    return render(request, 'inventario/seleccion_sucursal.html', {'sucursales': sucursales})

@login_required
def lista_productos(request):
    """Vista de la planilla móvil con resumen de subtotales para el usuario."""
    sucursal_id = request.GET.get('sucursal_id')
    if not sucursal_id:
        return redirect('seleccion_sucursal')
    
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    hoy = timezone.now().date()
    
    # MODIFICACIÓN: Ordenamos con prioridad para que las SALTEÑAS salgan adelante
    productos = Producto.objects.filter(sucursal=sucursal).select_related('categoria').annotate(
        prioridad=Case(
            When(categoria__nombre__icontains='SALTE', then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by('prioridad', 'categoria__nombre', 'nombre')
    
    ventas_hoy = VentaSalteña.objects.filter(sucursal=sucursal, fecha=hoy)
    gastos_hoy = GastoExtra.objects.filter(sucursal=sucursal, fecha=hoy)

    # Cálculo de Totales
    total_cantidad = ventas_hoy.aggregate(Sum('venta'))['venta__sum'] or 0
    total_ingreso = sum(v.total_bs for v in ventas_hoy)
    total_gastos = gastos_hoy.aggregate(Sum('monto'))['monto__sum'] or 0
    
    # Cálculo del Saldo Neto: $Saldo Neto = Ingreso Bruto - Gastos$
    total_neto = total_ingreso - total_gastos

    return render(request, 'inventario/lista.html', {
        'productos': productos, 
        'sucursal_activa': sucursal,
        'total_cantidad': total_cantidad,
        'total_ingreso': total_ingreso,
        'total_gastos': total_gastos,
        'total_neto': total_neto,
    })

# --- 2. REPORTES Y CONSULTAS ---

@login_required
def historial_ventas(request):
    """Muestra todos los cierres guardados."""
    cierres = CajaDiaria.objects.all().order_by('-fecha', '-id')
    return render(request, 'inventario/historial.html', {'cierres': cierres})

@login_required
def ver_planilla_html(request):
    """Visualización previa del reporte en formato web."""
    caja_id = request.GET.get('caja_id')
    cierre = get_object_or_404(CajaDiaria, id=caja_id)
    return render(request, 'inventario/pdf_template.html', {'cierre': cierre, 'es_vista_web': True})

# --- 3. PROCESAMIENTO DE DATOS ---

@login_required
def guardar_registro(request):
    """Guarda Inventario, Ventas, Traspasos y Gastos dinámicos."""
    if request.method == "POST":
        suc_id = request.POST.get('sucursal_id')
        suc_obj = get_object_or_404(Sucursal, id=suc_id)
        
        # 1. Guardar cierre financiero (Caja)
        caja = CajaDiaria.objects.create(
            sucursal=suc_obj,
            efectivo=float(request.POST.get('caja_efectivo') or 0),
            qr=float(request.POST.get('caja_qr') or 0),
            tarjetero=float(request.POST.get('caja_tarjeta') or 0)
        )

        # 2. Guardar Movimientos por Producto
        productos = Producto.objects.filter(sucursal=suc_obj)
        for p in productos:
            # Captura de datos del formulario
            v_cant = int(request.POST.get(f's_{p.id}') or 0)
            p_v = request.POST.get(f'p_{p.id}', 0)
            e_v = request.POST.get(f'e_{p.id}', 0)
            b_v = request.POST.get(f'b_{p.id}', 0)
            t_cant = request.POST.get(f't_cant_{p.id}', 0)
            t_suc = request.POST.get(f't_suc_{p.id}', '')

            # Guardar venta individual para el registro de ventas
            if v_cant > 0:
                VentaSalteña.objects.create(
                    producto=p.nombre, 
                    venta=v_cant,
                    precio_unitario=p.precio_unitario, 
                    sucursal=suc_obj
                )
            
            # Guardar registro diario (Inventario/PDF) incluyendo traspasos
            RegistroDiario.objects.create(
                producto=p,
                sucursal=suc_obj,
                produccion=int(p_v or 0),
                entrada=int(e_v or 0),
                baja=int(b_v or 0),
                traspaso=int(t_cant or 0),
                salida=v_cant
            )

        # 3. Guardar lista dinámica de Gastos Extras
        descs = request.POST.getlist('gasto_desc[]')
        montos = request.POST.getlist('gasto_monto[]')
        for d, m in zip(descs, montos):
            if d and m:
                GastoExtra.objects.create(
                    descripcion=d, 
                    monto=float(m), 
                    sucursal=suc_obj
                )

        return JsonResponse({"status": "success", "caja_id": caja.id})

# --- 4. GENERACIÓN DE PDF ---

@login_required
def generar_pdf_estilo_cuaderno(request):
    """Genera el PDF usando exactamente la estructura de tu plantilla original"""
    caja_id = request.GET.get('caja_id')
    cierre = get_object_or_404(CajaDiaria, id=caja_id)
    
    # MODIFICACIÓN: Aplicamos la misma prioridad para que en el PDF también salgan las Salteñas primero
    productos_sucursal = Producto.objects.filter(
        sucursal=cierre.sucursal
    ).select_related('categoria').annotate(
        prioridad=Case(
            When(categoria__nombre__icontains='SALTE', then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by('prioridad', 'categoria__nombre', 'nombre')

    # 2. Buscamos los registros de inventario de ese día
    registros_hoy = {
        r.producto_id: r 
        for r in RegistroDiario.objects.filter(
            sucursal=cierre.sucursal, 
            fecha_creacion__date=cierre.fecha
        )
    }

    # 3. Construimos la lista "filas" que pide tu plantilla
    filas = []
    total_ventas_bs = 0
    
    for p in productos_sucursal:
        reg = registros_hoy.get(p.id)
        if reg:
            # Sumamos al total solo lo que tiene registro de salida
            total_ventas_bs += (reg.salida * p.precio_unitario)
            
        # Creamos el objeto que tu HTML recorre como {{ fila.producto }} y {{ fila.reg }}
        filas.append({
            'producto': p,
            'reg': reg
        })
    
    total_caja_real = cierre.efectivo + cierre.qr + cierre.tarjetero
    diferencia = total_caja_real - total_ventas_bs

    # 4. Enviamos los datos al HTML (Nombres de variables exactos a tu plantilla)
    html_string = render_to_string('inventario/pdf_template.html', {
        'cierre': cierre,
        'filas': filas,  # Nombre exacto que usa tu {% for fila in filas %}
        'total_ventas': total_ventas_bs,
        'total_caja': total_caja_real,
        'diferencia': diferencia,
    })

    # 5. Generación del PDF
    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Reporte_{cierre.sucursal.nombre}.pdf"'
    return response