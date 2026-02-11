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

# Importación de WeasyPrint
from weasyprint import HTML

# --- 1. NAVEGACIÓN ---

@login_required
def seleccionar_sucursal(request):
    """Muestra las sucursales disponibles para trabajar."""
    sucursales = Sucursal.objects.all()
    return render(request, 'inventario/seleccion_sucursal.html', {'sucursales': sucursales})

@login_required
def lista_productos(request):
    """Vista de la planilla móvil con orden prioritario de Salteñas."""
    sucursal_id = request.GET.get('sucursal_id')
    if not sucursal_id:
        return redirect('seleccion_sucursal')
    
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    
    # Ordenamos con prioridad para que las SALTEÑAS salgan primero
    productos = Producto.objects.filter(sucursal=sucursal).select_related('categoria').annotate(
        prioridad=Case(
            When(categoria__nombre__icontains='SALTE', then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by('prioridad', 'categoria__nombre', 'nombre')
    
    return render(request, 'inventario/lista.html', {
        'productos': productos, 
        'sucursal_activa': sucursal,
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
    """Guarda Inventario, Ventas, Personal, Traspasos y Gastos."""
    if request.method == "POST":
        suc_id = request.POST.get('sucursal_id')
        suc_obj = get_object_or_404(Sucursal, id=suc_id)
        
        # Captura de personal de turno (Checkboxes)
        personal_seleccionado = request.POST.getlist('personal_turno')
        nombres_personal = ", ".join(personal_seleccionado)

        # 1. Guardar cierre financiero (Caja)
        caja = CajaDiaria.objects.create(
            sucursal=suc_obj,
            efectivo=float(request.POST.get('caja_efectivo') or 0),
            qr=float(request.POST.get('caja_qr') or 0),
            tarjetero=float(request.POST.get('caja_tarjeta') or 0),
            personal_turno=nombres_personal # Asegúrate de tener este campo en models.py
        )

        # 2. Guardar Movimientos por Producto
        productos = Producto.objects.filter(sucursal=suc_obj)
        for p in productos:
            v_cant = int(request.POST.get(f's_{p.id}') or 0)
            e_v = request.POST.get(f'e_{p.id}', 0)
            b_v = request.POST.get(f'b_{p.id}', 0)
            t_cant = request.POST.get(f't_cant_{p.id}', 0)
            t_suc = request.POST.get(f't_suc_{p.id}', '')

            if v_cant > 0:
                VentaSalteña.objects.create(
                    producto=p.nombre, 
                    venta=v_cant,
                    precio_unitario=p.precio_unitario, 
                    sucursal=suc_obj
                )
            
            # Guardar registro diario detallado
            RegistroDiario.objects.create(
                producto=p,
                sucursal=suc_obj,
                entrada=int(e_v or 0),
                baja=int(b_v or 0),
                traspaso=int(t_cant or 0),
                traspaso_destino=t_suc, # Guarda el nombre completo de la sucursal
                salida=v_cant
            )

        # 3. Guardar Gastos Extras
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
    """Genera, organiza y descarga automáticamente el reporte PDF."""
    caja_id = request.GET.get('caja_id')
    cierre = get_object_or_404(CajaDiaria, id=caja_id)
    
    # 1. Datos para el reporte (Salteñas primero)
    productos = Producto.objects.filter(sucursal=cierre.sucursal).annotate(
        prioridad=Case(When(categoria__nombre__icontains='SALTE', then=Value(1)), default=Value(2), output_field=IntegerField())
    ).order_by('prioridad', 'categoria__nombre', 'nombre')

    registros = {r.producto_id: r for r in RegistroDiario.objects.filter(
        sucursal=cierre.sucursal, 
        fecha_creacion__date=cierre.fecha
    )}
    
    gastos_extras = GastoExtra.objects.filter(sucursal=cierre.sucursal, fecha=cierre.fecha)

    filas = []
    total_ventas = 0
    tS, tJ = 0, 0 # Contadores para el tablero final

    for p in productos:
        reg = registros.get(p.id)
        v_bs = (reg.salida * p.precio_unitario) if reg else 0
        total_ventas += v_bs
        
        # Lógica de conteo por tipo
        cat_nombre = p.categoria.nombre.upper()
        cant_sale = reg.salida if reg else 0
        if 'SALTE' in cat_nombre: tS += cant_sale
        elif 'JUGO' in cat_nombre: tJ += cant_sale

        filas.append({
            'producto': p, 
            'reg': reg, 
            'total_fila_bs': v_bs
        })

    # 2. Cálculos consolidados
    total_gastos = sum(g.monto for g in gastos_extras)
    total_caja_real = cierre.efectivo + cierre.qr + cierre.tarjetero
    diferencia = total_caja_real - (total_ventas - total_gastos)

    context = {
        'cierre': cierre,
        'filas': filas,
        'gastos_extras': gastos_extras,
        'tS': tS, 'tJ': tJ,
        'total_ventas': total_ventas,
        'total_gastos': total_gastos,
        'total_caja': total_caja_real,
        'diferencia': diferencia,
    }

    # 3. Renderizado y DESCARGA (attachment)
    html_string = render_to_string('inventario/pdf_template.html', context)
    pdf = HTML(string=html_string).write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    nombre_archivo = f"Reporte_{cierre.sucursal.nombre}_{cierre.fecha}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    
    return response