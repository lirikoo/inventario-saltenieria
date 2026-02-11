from django.db import models
from django.contrib.auth.models import User

# 1. GESTIÓN DE TIENDAS Y SUCURSALES
class Sucursal(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    usuario_encargado = models.OneToOneField(
        User, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='sucursal_asignada'
    )

    def __str__(self):
        return self.nombre

# 2. PRODUCTOS Y CATEGORÍAS
class Categoria(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sucursal = models.ManyToManyField(Sucursal, related_name='productos')

    def __str__(self):
        return self.nombre

# 3. REGISTRO DE INVENTARIO DIARIO (Actualizado para el PDF)
class RegistroDiario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    produccion = models.IntegerField(default=0)
    entrada = models.IntegerField(default=0)
    baja = models.IntegerField(default=0)
    traspaso = models.IntegerField(default=0)
    # NUEVO: Guarda el nombre completo de la sucursal destino
    traspaso_destino = models.CharField(max_length=100, blank=True, null=True) 
    salida = models.IntegerField(default=0)

# 4. CIERRE DE CAJA FINANCIERO (Actualizado para Personal)
class CajaDiaria(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    qr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tarjetero = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # NUEVO: Guarda los nombres de los trabajadores seleccionados
    personal_turno = models.CharField(max_length=255, blank=True, null=True) 

    def __str__(self):
        return f"Cierre {self.sucursal.nombre} - {self.fecha}"

class Gasto(models.Model):
    caja = models.ForeignKey(CajaDiaria, on_delete=models.CASCADE, related_name='detalles_gastos')
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

# 5. REGISTRO DE VENTAS MÓVILES
class VentaSalteña(models.Model):
    producto = models.CharField(max_length=50)
    venta = models.IntegerField(default=0)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)

    @property
    def total_bs(self):
        return self.venta * self.precio_unitario

class GastoExtra(models.Model):
    descripcion = models.CharField(max_length=200, verbose_name="Descripción")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto (Bs)")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.descripcion} (-{self.monto} Bs)"