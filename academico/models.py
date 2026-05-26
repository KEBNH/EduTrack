from django.db import models
import uuid

class Employee(models.Model):
    class RolEmpleado(models.TextChoices):
        DIRECTOR = 'DIRECTOR', 'Director'
        PROFESOR = 'PROFESOR', 'Profesor'

    dni = models.CharField(max_length=8, blank=False, null=False)
    nombre = models.CharField(max_length=200, blank=False, null=False)
    apellidos = models.CharField(max_length=200, blank=False, null=False)
    celular = models.CharField(max_length=9, blank=True, null=True, default='')
    correo = models.EmailField(max_length=100, blank=True, null=True, default='')
    rol = models.CharField(max_length=15, choices=RolEmpleado.choices)
    activo = models.BooleanField(default=False)
    codigo_unico = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    fcreacion = models.DateTimeField(auto_now_add=True)
    fmodificaicon = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'