from django.db import models
from django.contrib.auth.models import User

class Sucursal(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    usuario_encargado = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sucursal_asignada')

    def __str__(self):
        return self.nombre

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

class RegistroDiario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    produccion = models.IntegerField(default=0)
    entrada = models.IntegerField(default=0)
    baja = models.IntegerField(default=0)
    traspaso = models.IntegerField(default=0)
    salida = models.IntegerField(default=0)

class CajaDiaria(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    qr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tarjetero = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Gasto(models.Model):
    caja = models.ForeignKey(CajaDiaria, on_delete=models.CASCADE, related_name='detalles_gastos')
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

class VentaSalteña(models.Model):
    OPCIONES_TRASPASO = [
        ('Dest', 'Destino'),
        ('Calacoto', 'Calacoto'),
        ('Mendez', 'Méndez'),
        ('San Pedro', 'San Pedro'),
    ]
    producto = models.CharField(max_length=50)
    venta = models.IntegerField(default=0)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)

    @property
    def total_bs(self):
        return self.venta * self.precio_unitario

class GastoExtra(models.Model):
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)