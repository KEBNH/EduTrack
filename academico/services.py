from django.db import transaction

from .models import Curso, MatriculaCurso


@transaction.atomic
def asignar_cursos_activos(matricula):
    cursos = Curso.objects.filter(
        institucion=matricula.institucion,
        grado=matricula.grado,
        activo=True,
    )
    existentes = set(
        MatriculaCurso.objects.filter(matricula=matricula).values_list(
            "curso_id", flat=True
        )
    )
    MatriculaCurso.objects.bulk_create(
        [
            MatriculaCurso(
                institucion=matricula.institucion,
                matricula=matricula,
                curso=curso,
            )
            for curso in cursos
            if curso.pk not in existentes
        ]
    )
