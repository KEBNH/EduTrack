from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Institucion(models.Model):
    nombre = models.CharField(max_length=150)
    codigo_modular = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.nombre


class Estudiante(models.Model):
    dni = models.CharField(max_length=8, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    institucion = models.ForeignKey(Institucion, on_delete=models.PROTECT, related_name="estudiantes")

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class Curso(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Asistencia(models.Model):
    ESTADO_ASISTIO = "asistio"
    ESTADO_FALTO = "falto"
    ESTADOS = [
        (ESTADO_ASISTIO, "Asistio"),
        (ESTADO_FALTO, "Falto"),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT, related_name="asistencias")
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="asistencias")
    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asistencias_registradas",
    )

    def __str__(self):
        return f"{self.estudiante} - {self.curso} - {self.fecha}"


class Calificacion(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT, related_name="calificaciones")
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="calificaciones")
    nota = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    periodo = models.CharField(max_length=50)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="calificaciones_registradas",
    )

    def __str__(self):
        return f"{self.estudiante} - {self.curso} - {self.nota}"


class AlertaRiesgo(models.Model):
    NIVEL_BAJO = "bajo"
    NIVEL_MEDIO = "medio"
    NIVEL_ALTO = "alto"
    NIVELES = [
        (NIVEL_BAJO, "Bajo"),
        (NIVEL_MEDIO, "Medio"),
        (NIVEL_ALTO, "Alto"),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT, related_name="alertas_riesgo")
    nivel = models.CharField(max_length=20, choices=NIVELES)
    motivo = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    esta_activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.estudiante} - {self.nivel}"
