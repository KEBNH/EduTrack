from django.contrib import admin

from .models import (
    Alerta,
    Alumno,
    Apoderado,
    Asistencia,
    Curso,
    Grado,
    Institucion,
    Matricula,
    MatriculaCurso,
    Nota,
)


admin.site.register(
    [
        Institucion,
        Alumno,
        Apoderado,
        Grado,
        Curso,
        Matricula,
        MatriculaCurso,
        Asistencia,
        Nota,
        Alerta,
    ]
)
