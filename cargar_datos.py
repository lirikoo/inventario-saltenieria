import os
import django

# Configuración del entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from inventario.models import Sucursal, Categoria, Producto

def cargar_planilla_cardelfi():
    print("Iniciando carga de datos Cardelfi...")

    # 1. Crear Sucursales
    sucursales = ['CALACOTO', 'MENDEZ ARCOS', 'SAN PEDRO']
    suc_objs_list = []
    for nombre in sucursales:
        obj, _ = Sucursal.objects.get_or_create(nombre=nombre)
        suc_objs_list.append(obj)
        print(f"Sucursal verificada: {nombre}")

    # 2. Definir Categorías y sus Productos (según tu cuaderno)
    datos = {
        'SALTEÑAS': [
            ('CARNE', 8.00), ('POLLO', 8.00), ('MIXTAS', 8.00), 
            ('SANTA CLARA', 8.00), ('SALTEÑAS HOJA', 8.00), ('QUESO', 8.00), ('FRICASE', 9.00)
        ],
        'BEBIDAS': [
            ('REFRESCO 190 ml', 3.00), ('REFRESCO 300 ml', 5.00), ('REFRESCO 500 ml', 7.00),
            ('REFRESCO 600 ml', 8.00), ('REFRESCO 2.5 lt', 15.00), ('AGUA 500 ml', 5.00),
            ('AGUA 3 lt', 12.00), ('LECHE', 6.00)
        ],
        'JUGOS': [
            ('PLÁTANO/PAPAYA', 12.00), ('BATIDO DE LIMON', 10.00), 
            ('FRUT/ARAND/MORA', 15.00), ('TROPICAL/FRUTO ROJOS', 15.00)
        ],
        'BEBIDAS CALIENTES': [
            ('TE O MATE', 5.00), ('LINAZA', 6.00), ('CAFÉ/COCOA', 7.00)
        ]
    }

    # 3. Insertar en la Base de Datos MySQL
    for nombre_cat, productos in datos.items():
        categoria_obj, _ = Categoria.objects.get_or_create(nombre=nombre_cat)
        
        for nombre_prod, precio in productos:
            # Creamos el producto (eliminado 'stock_actual' que no existe en models.py)
            producto_obj, creado = Producto.objects.get_or_create(
                nombre=nombre_prod,
                categoria=categoria_obj,
                defaults={'precio_unitario': precio}
            )
            
            # Asignamos el producto a todas las sucursales (relación ManyToMany)
            producto_obj.sucursal.set(suc_objs_list)

    print("¡Éxito! Categorías y productos creados y asignados a las 3 sucursales.")

if __name__ == '__main__':
    cargar_planilla_cardelfi()