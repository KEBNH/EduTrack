import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Institucion(models.Model):
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=30, unique=True)
    activo = models.BooleanField(default=True)
    codigo_unico = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    fcreacion = models.DateTimeField(auto_now_add=True)
    fmodificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "institucion"
        verbose_name_plural = "instituciones"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class ModeloInstitucional(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.PROTECT)
    codigo_unico = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    fcreacion = models.DateTimeField(auto_now_add=True)
    fmodificacion = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Alumno(ModeloInstitucional):
    dni = models.CharField("DNI", max_length=8)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    fecha_nacimiento = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("apellidos", "nombres")
        constraints = [
            models.UniqueConstraint(
                fields=("institucion", "dni"), name="alumno_dni_unico_institucion"
            )
        ]

    def __str__(self):
        return f"{self.apellidos}, {self.nombres}"


class Apoderado(ModeloInstitucional):
    class Parentesco(models.TextChoices):
        PADRE = "PADRE", "Padre"
        MADRE = "MADRE", "Madre"
        TUTOR = "TUTOR", "Tutor legal"
        OTRO = "OTRO", "Otro"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="perfil_apoderado",
        null=True,
        blank=True,
    )
    alumnos = models.ManyToManyField(Alumno, related_name="apoderados", blank=True)
    dni = models.CharField("DNI", max_length=8)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    celular = models.CharField(max_length=9)
    correo = models.EmailField(blank=True)
    parentesco = models.CharField(max_length=10, choices=Parentesco.choices)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("apellidos", "nombres")
        constraints = [
            models.UniqueConstraint(
                fields=("institucion", "dni"), name="apoderado_dni_unico_institucion"
            )
        ]

    def __str__(self):
        return f"{self.apellidos}, {self.nombres}"


class Grado(ModeloInstitucional):
    class Nivel(models.TextChoices):
        PRIMARIA = "PRIMARIA", "Primaria"
        SECUNDARIA = "SECUNDARIA", "Secundaria"

    nivel = models.CharField(max_length=12, choices=Nivel.choices)
    nombre = models.CharField(max_length=50)
    seccion = models.CharField(max_length=10)
    anio_academico = models.PositiveSmallIntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("-anio_academico", "nivel", "nombre", "seccion")
        constraints = [
            models.UniqueConstraint(
                fields=("institucion", "anio_academico", "nivel", "nombre", "seccion"),
                name="grado_unico_institucion_anio",
            )
        ]

    def __str__(self):
        return f"{self.nombre} {self.seccion} - {self.nivel} ({self.anio_academico})"


class Curso(ModeloInstitucional):
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=30)
    grado = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="cursos")
    profesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cursos_asignados",
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("nombre",)
        constraints = [
            models.UniqueConstraint(
                fields=("institucion", "codigo", "grado"),
                name="curso_codigo_unico_grado",
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.grado}"


class Matricula(ModeloInstitucional):
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        RETIRADA = "RETIRADA", "Retirada"
        FINALIZADA = "FINALIZADA", "Finalizada"

    alumno = models.ForeignKey(Alumno, on_delete=models.PROTECT, related_name="matriculas")
    grado = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="matriculas")
    anio_academico = models.PositiveSmallIntegerField()
    fecha_matricula = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ACTIVA)

    class Meta:
        ordering = ("-anio_academico", "alumno__apellidos")
        constraints = [
            models.UniqueConstraint(
                fields=("institucion", "alumno", "anio_academico"),
                name="matricula_unica_alumno_anio",
            )
        ]

    def __str__(self):
        return f"{self.alumno} - {self.grado}"


class Asistencia(ModeloInstitucional):
    class Estado(models.TextChoices):
        PRESENTE = "PRESENTE", "Presente"
        AUSENTE = "AUSENTE", "Ausente"
        TARDANZA = "TARDANZA", "Tardanza"

    matricula = models.ForeignKey(
        Matricula, on_delete=models.CASCADE, related_name="asistencias"
    )
    fecha = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices)
    observacion = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ("-fecha",)
        constraints = [
            models.UniqueConstraint(
                fields=("matricula", "fecha"), name="asistencia_unica_matricula_fecha"
            )
        ]

    def __str__(self):
        return f"{self.matricula.alumno} - {self.fecha}: {self.get_estado_display()}"


class Nota(ModeloInstitucional):
    class Periodo(models.TextChoices):
        PRIMERO = "1", "Primer periodo"
        SEGUNDO = "2", "Segundo periodo"
        TERCERO = "3", "Tercer periodo"
        CUARTO = "4", "Cuarto periodo"

    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name="notas")
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="notas")
    periodo = models.CharField(max_length=1, choices=Periodo.choices)
    evaluacion = models.CharField(max_length=100)
    calificacion = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )

    class Meta:
        ordering = ("-fcreacion",)
        constraints = [
            models.UniqueConstraint(
                fields=("matricula", "curso", "periodo", "evaluacion"),
                name="nota_unica_evaluacion",
            )
        ]

    def __str__(self):
        return f"{self.matricula.alumno} - {self.curso}: {self.calificacion}"


class Alerta(ModeloInstitucional):
    class Tipo(models.TextChoices):
        ASISTENCIA = "ASISTENCIA", "Asistencia"
        RENDIMIENTO = "RENDIMIENTO", "Rendimiento academico"

    class NivelRiesgo(models.TextChoices):
        BAJO = "BAJO", "Bajo"
        MEDIO = "MEDIO", "Medio"
        ALTO = "ALTO", "Alto"

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="alertas")
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    nivel_riesgo = models.CharField(max_length=10, choices=NivelRiesgo.choices)
    descripcion = models.TextField()
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ("-fcreacion",)

    def __str__(self):
        return f"{self.alumno} - {self.get_tipo_display()} ({self.get_nivel_riesgo_display()})"
