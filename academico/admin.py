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
    Nota,
)


admin.site.register(
    [Institucion, Alumno, Apoderado, Grado, Curso, Matricula, Asistencia, Nota, Alerta]
)
