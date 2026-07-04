import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


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
    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="grados_tutoreados",
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("-anio_academico", "nivel", "nombre", "seccion")
        constraints = [
            models.UniqueConstraint(
                fields=("institucion", "anio_academico", "nivel", "nombre", "seccion"),
                name="grado_unico_institucion_anio",
            )
        ]

    def clean(self):
        errors = {}
        if self.tutor_id:
            if self.institucion_id != self.tutor.institucion_id:
                errors["tutor"] = (
                    "El tutor debe pertenecer a la misma institucion del grado."
                )
            elif self.tutor.rol != "PROFESOR":
                errors["tutor"] = "El tutor asignado debe tener el rol Profesor."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.nombre} {self.seccion} - "
            f"{self.get_nivel_display()} ({self.anio_academico})"
        )


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
                Lower("codigo"),
                "institucion",
                "grado",
                name="curso_codigo_unico_grado",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                "institucion",
                "grado",
                name="curso_nombre_unico_grado",
            ),
        ]

    def clean(self):
        errors = {}
        if self.grado_id and self.institucion_id != self.grado.institucion_id:
            errors["grado"] = "El grado debe pertenecer a la misma institucion del curso."
        if self.profesor_id:
            if self.institucion_id != self.profesor.institucion_id:
                errors["profesor"] = (
                    "El profesor debe pertenecer a la misma institucion del curso."
                )
            elif self.profesor.rol != "PROFESOR":
                errors["profesor"] = "El usuario asignado debe tener el rol Profesor."
        if self.grado_id and self.nombre:
            nombre_repetido = Curso.objects.filter(
                grado_id=self.grado_id, nombre__iexact=self.nombre
            ).exclude(pk=self.pk)
            if nombre_repetido.exists():
                errors["nombre"] = (
                    "Ya existe un curso con este nombre dentro del grado."
                )
        if self.grado_id and self.codigo:
            codigo_repetido = Curso.objects.filter(
                grado_id=self.grado_id, codigo__iexact=self.codigo
            ).exclude(pk=self.pk)
            if codigo_repetido.exists():
                errors["codigo"] = (
                    "Ya existe un curso con este codigo dentro del grado."
                )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.nombre} - {self.grado}"


class Matricula(ModeloInstitucional):
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        RETIRADA = "RETIRADA", "Retirada"
        FINALIZADA = "FINALIZADA", "Finalizada"

    alumno = models.ForeignKey(Alumno, on_delete=models.PROTECT, related_name="matriculas")
    grado = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="matriculas")
    anio_academico = models.PositiveSmallIntegerField(editable=False)
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

    def clean(self):
        errors = {}
        if self.alumno_id and self.institucion_id != self.alumno.institucion_id:
            errors["alumno"] = (
                "El alumno debe pertenecer a la misma institucion de la matricula."
            )
        if self.grado_id:
            if self.institucion_id != self.grado.institucion_id:
                errors["grado"] = (
                    "El grado debe pertenecer a la misma institucion de la matricula."
                )
            self.anio_academico = self.grado.anio_academico
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.grado_id:
            self.anio_academico = self.grado.anio_academico
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.alumno} - {self.grado}"


class MatriculaCurso(ModeloInstitucional):
    matricula = models.ForeignKey(
        Matricula, on_delete=models.PROTECT, related_name="cursos_matriculados"
    )
    curso = models.ForeignKey(
        Curso, on_delete=models.PROTECT, related_name="matriculas_curso"
    )

    class Meta:
        ordering = ("curso__nombre",)
        constraints = [
            models.UniqueConstraint(
                fields=("matricula", "curso"), name="matricula_curso_unica"
            )
        ]

    def clean(self):
        errors = {}
        if self.matricula_id and self.institucion_id != self.matricula.institucion_id:
            errors["matricula"] = (
                "La matricula debe pertenecer a la misma institucion."
            )
        if self.curso_id:
            if self.institucion_id != self.curso.institucion_id:
                errors["curso"] = "El curso debe pertenecer a la misma institucion."
            elif self.matricula_id and self.curso.grado_id != self.matricula.grado_id:
                errors["curso"] = "El curso debe pertenecer al grado de la matricula."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.matricula.alumno} - {self.curso}"


class Asistencia(ModeloInstitucional):
    class Estado(models.TextChoices):
        PRESENTE = "PRESENTE", "Presente"
        FALTA = "FALTA", "Falta"

    matricula_curso = models.ForeignKey(
        MatriculaCurso, on_delete=models.PROTECT, related_name="asistencias"
    )
    fecha = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices)
    observacion = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ("-fecha",)
        constraints = [
            models.UniqueConstraint(
                fields=("matricula_curso", "fecha"),
                name="asistencia_unica_alumno_curso_fecha",
            )
        ]

    def clean(self):
        errors = {}
        if (
            self.matricula_curso_id
            and self.institucion_id != self.matricula_curso.institucion_id
        ):
            errors["matricula_curso"] = (
                "El curso matriculado debe pertenecer a la misma institucion."
            )
        if (
            self._state.adding
            and self.matricula_curso_id
            and self.matricula_curso.matricula.estado != Matricula.Estado.ACTIVA
        ):
            errors["matricula_curso"] = (
                "No se puede registrar asistencia en una matricula inactiva."
            )
        if self.fecha:
            from .services import obtener_bimestre

            if self.fecha.weekday() >= 5:
                errors["fecha"] = "No se puede registrar asistencia en fin de semana."
            elif obtener_bimestre(self.fecha) is None:
                errors["fecha"] = "La fecha no pertenece a ningun bimestre academico."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.matricula_curso.matricula.alumno} - "
            f"{self.matricula_curso.curso} - {self.fecha}: {self.get_estado_display()}"
        )


class Nota(ModeloInstitucional):
    class Periodo(models.TextChoices):
        PRIMERO = "1", "Primer periodo"
        SEGUNDO = "2", "Segundo periodo"
        TERCERO = "3", "Tercer periodo"
        CUARTO = "4", "Cuarto periodo"

    matricula_curso = models.ForeignKey(
        MatriculaCurso, on_delete=models.PROTECT, related_name="notas"
    )
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
                fields=("matricula_curso", "periodo", "evaluacion"),
                name="nota_unica_evaluacion",
            )
        ]

    def clean(self):
        errors = {}
        if (
            self.matricula_curso_id
            and self.institucion_id != self.matricula_curso.institucion_id
        ):
            errors["matricula_curso"] = (
                "El curso matriculado debe pertenecer a la misma institucion."
            )
        if (
            self._state.adding
            and self.matricula_curso_id
            and self.matricula_curso.matricula.estado != Matricula.Estado.ACTIVA
        ):
            errors["matricula_curso"] = (
                "No se puede registrar una nota en una matricula inactiva."
            )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.matricula_curso.matricula.alumno} - "
            f"{self.matricula_curso.curso}: {self.calificacion}"
        )


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

    def clean(self):
        if self.alumno_id and self.institucion_id != self.alumno.institucion_id:
            raise ValidationError(
                {
                    "alumno": (
                        "El alumno debe pertenecer a la misma institucion de la alerta."
                    )
                }
            )

    def __str__(self):
        return f"{self.alumno} - {self.get_tipo_display()} ({self.get_nivel_riesgo_display()})"
