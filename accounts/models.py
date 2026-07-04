import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class CustomUser(AbstractUser):
    class Rol(models.TextChoices):
        IT = "IT", "IT / Soporte Tecnico"
        MINEDU = "MINEDU", "Empleado MINEDU"
        DIRECTOR = "DIRECTOR", "Director"
        PROFESOR = "PROFESOR", "Profesor"
        PERSONAL_ACADEMICO = "PERSONAL_ACADEMICO", "Personal Academico"
        APODERADO = "APODERADO", "Padre/Apoderado"

    username = None
    email = models.EmailField("correo electronico", unique=True)
    dni = models.CharField("DNI", max_length=8, unique=True)
    celular = models.CharField(max_length=9, blank=True)
    rol = models.CharField(max_length=30, choices=Rol.choices, blank=True)
    institucion = models.ForeignKey(
        "academico.Institucion",
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="usuarios_creados",
        null=True,
        blank=True,
    )
    codigo_unico = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    fmodificacion = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["dni"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def estado_cuenta(self):
        if not self.is_active:
            return "INACTIVO"
        if not self.has_usable_password():
            return "PENDIENTE"
        return "ACTIVO"

    @property
    def estado_cuenta_display(self):
        estados = {
            "INACTIVO": "Inactivo",
            "PENDIENTE": "Activación pendiente",
            "ACTIVO": "Activo",
        }
        return estados[self.estado_cuenta]
