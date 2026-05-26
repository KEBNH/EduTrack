from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Institucion(models.Model):
    nombre = models.CharField("nombre", max_length=150)
    codigo_modular = models.CharField("código modular", max_length=20, unique=True)

    class Meta:
        verbose_name = "institución"
        verbose_name_plural = "instituciones"

    def __str__(self):
        return self.nombre


class Estudiante(models.Model):
    dni = models.CharField("DNI", max_length=8, unique=True)
    nombres = models.CharField("nombres", max_length=100)
    apellidos = models.CharField("apellidos", max_length=100)
    institucion = models.ForeignKey(
        Institucion,
        verbose_name="institución",
        on_delete=models.PROTECT,
        related_name="estudiantes",
    )

    class Meta:
        verbose_name = "estudiante"
        verbose_name_plural = "estudiantes"

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class Curso(models.Model):
    nombre = models.CharField("nombre", max_length=100, unique=True)

    class Meta:
        verbose_name = "curso"
        verbose_name_plural = "cursos"

    def __str__(self):
        return self.nombre


class Asistencia(models.Model):
    ESTADO_ASISTIO = "asistio"
    ESTADO_FALTO = "falto"
    ESTADOS = [
        (ESTADO_ASISTIO, "Asistió"),
        (ESTADO_FALTO, "Faltó"),
    ]

    estudiante = models.ForeignKey(
        Estudiante,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="asistencias",
    )
    curso = models.ForeignKey(
        Curso,
        verbose_name="curso",
        on_delete=models.PROTECT,
        related_name="asistencias",
    )
    fecha = models.DateField("fecha")
    estado = models.CharField("estado", max_length=20, choices=ESTADOS)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        on_delete=models.PROTECT,
        related_name="asistencias_registradas",
    )

    class Meta:
        verbose_name = "asistencia"
        verbose_name_plural = "asistencias"

    def __str__(self):
        return f"{self.estudiante} - {self.curso} - {self.fecha}"


class Calificacion(models.Model):
    estudiante = models.ForeignKey(
        Estudiante,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="calificaciones",
    )
    curso = models.ForeignKey(
        Curso,
        verbose_name="curso",
        on_delete=models.PROTECT,
        related_name="calificaciones",
    )
    nota = models.DecimalField(
        "nota",
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    periodo = models.CharField("periodo", max_length=50)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        on_delete=models.PROTECT,
        related_name="calificaciones_registradas",
    )

    class Meta:
        verbose_name = "calificación"
        verbose_name_plural = "calificaciones"

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

    estudiante = models.ForeignKey(
        Estudiante,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="alertas_riesgo",
    )
    nivel = models.CharField("nivel", max_length=20, choices=NIVELES)
    motivo = models.TextField("motivo")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    esta_activa = models.BooleanField("está activa", default=True)

    class Meta:
        verbose_name = "alerta de riesgo"
        verbose_name_plural = "alertas de riesgo"

    def __str__(self):
        return f"{self.estudiante} - {self.nivel}"
