from django.urls import path

from . import views

app_name = "academico"

urlpatterns = [
    path("inscripciones/crear/", views.inscripcion_crear, name="inscripcion_crear"),
    path("alumnos/", views.AlumnoListView.as_view(), name="alumno_lista"),
    path("alumnos/crear/", views.AlumnoCreateView.as_view(), name="alumno_crear"),
    path("alumnos/<int:pk>/editar/", views.AlumnoUpdateView.as_view(), name="alumno_editar"),
    path("apoderados/", views.ApoderadoListView.as_view(), name="apoderado_lista"),
    path("apoderados/crear/", views.ApoderadoCreateView.as_view(), name="apoderado_crear"),
    path("apoderados/<int:pk>/editar/", views.ApoderadoUpdateView.as_view(), name="apoderado_editar"),
    path("grados/", views.GradoListView.as_view(), name="grado_lista"),
    path("grados/crear/", views.GradoCreateView.as_view(), name="grado_crear"),
    path("grados/<int:pk>/editar/", views.GradoUpdateView.as_view(), name="grado_editar"),
    path("cursos/", views.CursoListView.as_view(), name="curso_lista"),
    path("cursos/crear/", views.CursoCreateView.as_view(), name="curso_crear"),
    path("cursos/<int:pk>/editar/", views.CursoUpdateView.as_view(), name="curso_editar"),
    path("matriculas/", views.MatriculaListView.as_view(), name="matricula_lista"),
    path("matriculas/crear/", views.MatriculaCreateView.as_view(), name="matricula_crear"),
    path("matriculas/<int:pk>/editar/", views.MatriculaUpdateView.as_view(), name="matricula_editar"),
    path("asistencias/", views.AsistenciaListView.as_view(), name="asistencia_lista"),
    path("asistencias/crear/", views.AsistenciaCreateView.as_view(), name="asistencia_crear"),
    path("asistencias/<int:pk>/editar/", views.AsistenciaUpdateView.as_view(), name="asistencia_editar"),
    path("notas/", views.NotaListView.as_view(), name="nota_lista"),
    path("notas/crear/", views.NotaCreateView.as_view(), name="nota_crear"),
    path("notas/<int:pk>/editar/", views.NotaUpdateView.as_view(), name="nota_editar"),
    path("alertas/", views.AlertaListView.as_view(), name="alerta_lista"),
    path("alertas/<int:pk>/cerrar/", views.alerta_cerrar, name="alerta_cerrar"),
    path("reportes/director/", views.reporte_director, name="reporte_director"),
    path("reportes/minedu/", views.reporte_minedu, name="reporte_minedu"),
    path("portal/", views.portal_apoderado, name="portal_apoderado"),
]
