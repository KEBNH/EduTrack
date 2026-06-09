from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import CreateView, ListView, UpdateView

from accounts.models import CustomUser
from accounts.services import capacidades_para

from .forms import (
    AlumnoForm,
    ApoderadoForm,
    AsistenciaForm,
    CursoForm,
    GradoForm,
    MatriculaForm,
    NotaForm,
)
from .models import Alumno, Apoderado, Asistencia, Curso, Grado, Matricula, Nota


ROL_PERSONAL = {CustomUser.Rol.PERSONAL_ACADEMICO}
ROLES_REGISTRO_ACADEMICO = {CustomUser.Rol.PROFESOR, CustomUser.Rol.PERSONAL_ACADEMICO}
ROLES_LECTURA_ACADEMICA = {
    CustomUser.Rol.DIRECTOR,
    CustomUser.Rol.PROFESOR,
    CustomUser.Rol.PERSONAL_ACADEMICO,
}


@login_required
def inicio(request):
    return render(
        request,
        "bashboard.html",
        {"capacidades": capacidades_para(request.user)},
    )


class PermisoRolMixin(LoginRequiredMixin, UserPassesTestMixin):
    roles_permitidos = set()
    raise_exception = True

    def test_func(self):
        return (
            self.request.user.is_active
            and self.request.user.rol in self.roles_permitidos
            and self.request.user.institucion_id is not None
        )


class ListaInstitucionalMixin(PermisoRolMixin):
    roles_permitidos = ROLES_LECTURA_ACADEMICA
    context_object_name = "objetos"
    template_name = "academico/model_list.html"
    titulo = ""
    url_crear = ""

    def get_queryset(self):
        return super().get_queryset().filter(institucion=self.request.user.institucion)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"titulo": self.titulo, "url_crear": self.url_crear})
        return context


class FormularioInstitucionalMixin(PermisoRolMixin):
    template_name = "academico/model_form.html"
    titulo = ""
    url_lista = ""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario_actual"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.institucion = self.request.user.institucion
        return super().form_valid(form)

    def get_queryset(self):
        return super().get_queryset().filter(institucion=self.request.user.institucion)

    def get_success_url(self):
        return reverse(self.url_lista)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"titulo": self.titulo, "url_lista": self.url_lista})
        return context


class AlumnoListView(ListaInstitucionalMixin, ListView):
    model = Alumno
    titulo = "Alumnos"
    url_crear = "academico:alumno_crear"


class AlumnoCreateView(FormularioInstitucionalMixin, CreateView):
    model = Alumno
    form_class = AlumnoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Registrar alumno"
    url_lista = "academico:alumno_lista"


class AlumnoUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Alumno
    form_class = AlumnoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar alumno"
    url_lista = "academico:alumno_lista"


class ApoderadoListView(ListaInstitucionalMixin, ListView):
    model = Apoderado
    titulo = "Padres y apoderados"
    url_crear = "academico:apoderado_crear"


class ApoderadoCreateView(FormularioInstitucionalMixin, CreateView):
    model = Apoderado
    form_class = ApoderadoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Registrar padre/apoderado"
    url_lista = "academico:apoderado_lista"


class ApoderadoUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Apoderado
    form_class = ApoderadoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar padre/apoderado"
    url_lista = "academico:apoderado_lista"


class GradoListView(ListaInstitucionalMixin, ListView):
    model = Grado
    titulo = "Grados"
    url_crear = "academico:grado_crear"


class GradoCreateView(FormularioInstitucionalMixin, CreateView):
    model = Grado
    form_class = GradoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Registrar grado"
    url_lista = "academico:grado_lista"


class GradoUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Grado
    form_class = GradoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar grado"
    url_lista = "academico:grado_lista"


class CursoListView(ListaInstitucionalMixin, ListView):
    model = Curso
    titulo = "Cursos"
    url_crear = "academico:curso_crear"


class CursoCreateView(FormularioInstitucionalMixin, CreateView):
    model = Curso
    form_class = CursoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Registrar curso"
    url_lista = "academico:curso_lista"


class CursoUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Curso
    form_class = CursoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar curso"
    url_lista = "academico:curso_lista"


class MatriculaListView(ListaInstitucionalMixin, ListView):
    model = Matricula
    titulo = "Matriculas"
    url_crear = "academico:matricula_crear"


class MatriculaCreateView(FormularioInstitucionalMixin, CreateView):
    model = Matricula
    form_class = MatriculaForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Matricular alumno"
    url_lista = "academico:matricula_lista"


class MatriculaUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Matricula
    form_class = MatriculaForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar matricula"
    url_lista = "academico:matricula_lista"


class AsistenciaListView(ListaInstitucionalMixin, ListView):
    model = Asistencia
    titulo = "Asistencias"
    url_crear = "academico:asistencia_crear"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.rol == CustomUser.Rol.PROFESOR:
            queryset = queryset.filter(
                matricula__grado__cursos__profesor=self.request.user
            ).distinct()
        return queryset


class AsistenciaCreateView(FormularioInstitucionalMixin, CreateView):
    model = Asistencia
    form_class = AsistenciaForm
    roles_permitidos = ROLES_REGISTRO_ACADEMICO
    titulo = "Registrar asistencia"
    url_lista = "academico:asistencia_lista"


class AsistenciaUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Asistencia
    form_class = AsistenciaForm
    roles_permitidos = ROLES_REGISTRO_ACADEMICO
    titulo = "Editar asistencia"
    url_lista = "academico:asistencia_lista"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.rol == CustomUser.Rol.PROFESOR:
            queryset = queryset.filter(
                matricula__grado__cursos__profesor=self.request.user
            ).distinct()
        return queryset


class NotaListView(ListaInstitucionalMixin, ListView):
    model = Nota
    titulo = "Notas"
    url_crear = "academico:nota_crear"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.rol == CustomUser.Rol.PROFESOR:
            queryset = queryset.filter(curso__profesor=self.request.user)
        return queryset


class NotaCreateView(FormularioInstitucionalMixin, CreateView):
    model = Nota
    form_class = NotaForm
    roles_permitidos = ROLES_REGISTRO_ACADEMICO
    titulo = "Registrar nota"
    url_lista = "academico:nota_lista"


class NotaUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Nota
    form_class = NotaForm
    roles_permitidos = ROLES_REGISTRO_ACADEMICO
    titulo = "Editar nota"
    url_lista = "academico:nota_lista"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.rol == CustomUser.Rol.PROFESOR:
            queryset = queryset.filter(curso__profesor=self.request.user)
        return queryset
