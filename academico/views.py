from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, ListView, UpdateView
from accounts.models import CustomUser
from accounts.services import capacidades_para
from datetime import date

from .forms import (
    AlumnoForm,
    ApoderadoForm,
    AsistenciaForm,
    CursoForm,
    GradoForm,
    InscripcionForm,
    MatriculaForm,
    NotaForm,
)
from .models import Alerta, Alumno, Apoderado, Asistencia, Curso, Grado, Institucion, Matricula, Nota
from .services import (
    asignar_cursos_activos,
    asignar_matriculas_activas,
    registrar_inscripcion,
    anios_disponibles_alumno,
    obtener_rango_bimestre,
    calcular_riesgo_asistencia, 
    calcular_riesgo_rendimiento,
    notas_por_bimestre,
    calendario_asistencia_bimestre,
)

ROL_PERSONAL = {CustomUser.Rol.PERSONAL_ACADEMICO}
ROLES_REGISTRO_ACADEMICO = {CustomUser.Rol.PROFESOR}
ROLES_LECTURA_ACADEMICA = {
    CustomUser.Rol.DIRECTOR,
    CustomUser.Rol.PROFESOR,
    CustomUser.Rol.PERSONAL_ACADEMICO,
}
ROLES_ALERTAS = {
    CustomUser.Rol.DIRECTOR,
    CustomUser.Rol.PROFESOR,
    CustomUser.Rol.PERSONAL_ACADEMICO,
    CustomUser.Rol.APODERADO,
}
ROLES_CIERRE_ALERTAS = {
    CustomUser.Rol.DIRECTOR,
    CustomUser.Rol.PERSONAL_ACADEMICO,
}
ALERTAS_POPUP_SESSION_KEY = "alertas_popup_mostrado"


def alertas_visibles_para(usuario):
    if (
        not usuario.is_active
        or usuario.rol not in ROLES_ALERTAS
        or usuario.institucion_id is None
    ):
        return Alerta.objects.none()

    queryset = Alerta.objects.filter(institucion=usuario.institucion)
    if usuario.rol == CustomUser.Rol.PROFESOR:
        queryset = queryset.filter(
            alumno__matriculas__cursos_matriculados__curso__profesor=usuario
        ).distinct()
    elif usuario.rol == CustomUser.Rol.APODERADO:
        queryset = queryset.filter(alumno__apoderados__usuario=usuario).distinct()
    return queryset

@login_required
def inicio(request):
    context = {"capacidades": capacidades_para(request.user)}
    if not request.session.get(ALERTAS_POPUP_SESSION_KEY):
        alertas_activas = (
            alertas_visibles_para(request.user)
            .filter(activa=True)
            .select_related("alumno")
        )
        total_alertas = alertas_activas.count()
        if total_alertas:
            context["alertas_popup"] = {
                "total": total_alertas,
                "altas": alertas_activas.filter(
                    nivel_riesgo=Alerta.NivelRiesgo.ALTO
                ).count(),
                "medias": alertas_activas.filter(
                    nivel_riesgo=Alerta.NivelRiesgo.MEDIO
                ).count(),
                "recientes": list(alertas_activas[:5]),
            }
            request.session[ALERTAS_POPUP_SESSION_KEY] = True

    if request.user.rol == CustomUser.Rol.APODERADO:
        try:
            perfil_apoderado = request.user.perfil_apoderado
        except Apoderado.DoesNotExist:
            perfil_apoderado = None
        context["hijos_apoderado"] = (
            perfil_apoderado.alumnos.all() if perfil_apoderado else Alumno.objects.none()
        )

    return render(
        request,
        "bashboard.html",
        context,
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
        context.update(
            {
                "titulo": self.titulo,
                "url_crear": self.url_crear,
                "puede_crear": (
                    bool(self.url_crear)
                    and self.request.user.rol == CustomUser.Rol.PERSONAL_ACADEMICO
                ),
            }
        )
        return context


class FormularioInstitucionalMixin(PermisoRolMixin):
    template_name = "academico/model_form.html"
    titulo = ""
    url_lista = ""
    mensaje_exito = "Registro guardado correctamente."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario_actual"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.institucion = self.request.user.institucion
        response = super().form_valid(form)
        messages.success(self.request, self.mensaje_exito)
        return response

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
    template_name = "academico/alumno_list.html"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        consulta = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "").strip()
        if consulta:
            queryset = queryset.filter(
                Q(dni__icontains=consulta)
                | Q(nombres__icontains=consulta)
                | Q(apellidos__icontains=consulta)
            )
        if estado == "ACTIVO":
            queryset = queryset.filter(activo=True)
        elif estado == "INACTIVO":
            queryset = queryset.filter(activo=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "puede_editar": self.request.user.rol == CustomUser.Rol.PERSONAL_ACADEMICO,
            }
        )
        return context


class AlumnoCreateView(FormularioInstitucionalMixin, CreateView):
    model = Alumno
    form_class = AlumnoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Registrar alumno"
    url_lista = "academico:alumno_lista"
    mensaje_exito = "Alumno registrado correctamente."


class AlumnoUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Alumno
    form_class = AlumnoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar alumno"
    url_lista = "academico:alumno_lista"
    mensaje_exito = "Datos del alumno actualizados correctamente."


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


@login_required
def inscripcion_crear(request):
    if (
        not request.user.is_active
        or request.user.rol != CustomUser.Rol.PERSONAL_ACADEMICO
        or request.user.institucion_id is None
    ):
        raise PermissionDenied("No tiene permiso para registrar inscripciones.")

    if request.method == "POST":
        form = InscripcionForm(request.POST, usuario_actual=request.user)
        if form.is_valid():
            try:
                registrar_inscripcion(
                    usuario_actual=request.user,
                    datos=form.cleaned_data,
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    "Inscripcion registrada y apoderado vinculado correctamente.",
                )
                return redirect("academico:matricula_lista")
    else:
        form = InscripcionForm(usuario_actual=request.user)

    return render(
        request,
        "academico/inscripcion_form.html",
        {"form": form, "titulo": "Registrar inscripcion"},
    )


class GradoListView(ListaInstitucionalMixin, ListView):
    model = Grado
    titulo = "Grados"
    url_crear = "academico:grado_crear"
    template_name = "academico/grado_list.html"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related("tutor")
        consulta = self.request.GET.get("q", "").strip()
        nivel = self.request.GET.get("nivel", "").strip()
        anio = self.request.GET.get("anio", "").strip()
        estado = self.request.GET.get("estado", "").strip()
        if consulta:
            queryset = queryset.filter(
                Q(nombre__icontains=consulta) | Q(seccion__icontains=consulta)
            )
        if nivel in Grado.Nivel.values:
            queryset = queryset.filter(nivel=nivel)
        if anio.isdigit():
            queryset = queryset.filter(anio_academico=int(anio))
        if estado == "ACTIVO":
            queryset = queryset.filter(activo=True)
        elif estado == "INACTIVO":
            queryset = queryset.filter(activo=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "nivel": self.request.GET.get("nivel", "").strip(),
                "anio": self.request.GET.get("anio", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "niveles": Grado.Nivel.choices,
                "puede_editar": self.request.user.rol == CustomUser.Rol.PERSONAL_ACADEMICO,
            }
        )
        return context


class GradoCreateView(FormularioInstitucionalMixin, CreateView):
    model = Grado
    form_class = GradoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Registrar grado"
    url_lista = "academico:grado_lista"
    mensaje_exito = "Grado registrado correctamente."


class GradoUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Grado
    form_class = GradoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar grado"
    url_lista = "academico:grado_lista"
    mensaje_exito = "Datos del grado actualizados correctamente."


class CursoListView(ListaInstitucionalMixin, ListView):
    model = Curso
    titulo = "Cursos"
    url_crear = "academico:curso_crear"
    template_name = "academico/curso_list.html"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related("grado", "profesor")
        consulta = self.request.GET.get("q", "").strip()
        grado = self.request.GET.get("grado", "").strip()
        profesor = self.request.GET.get("profesor", "").strip()
        estado = self.request.GET.get("estado", "").strip()
        if consulta:
            queryset = queryset.filter(
                Q(codigo__icontains=consulta) | Q(nombre__icontains=consulta)
            )
        if grado.isdigit():
            queryset = queryset.filter(grado_id=int(grado))
        if profesor.isdigit():
            queryset = queryset.filter(profesor_id=int(profesor))
        if estado == "ACTIVO":
            queryset = queryset.filter(activo=True)
        elif estado == "INACTIVO":
            queryset = queryset.filter(activo=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institucion = self.request.user.institucion
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "grado_seleccionado": self.request.GET.get("grado", "").strip(),
                "profesor_seleccionado": self.request.GET.get("profesor", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "grados": Grado.objects.filter(institucion=institucion),
                "profesores": CustomUser.objects.filter(
                    institucion=institucion, rol=CustomUser.Rol.PROFESOR
                ).order_by("last_name", "first_name"),
                "puede_editar": self.request.user.rol == CustomUser.Rol.PERSONAL_ACADEMICO,
            }
        )
        return context


class CursoCreateView(FormularioInstitucionalMixin, CreateView):
    model = Curso
    form_class = CursoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Registrar curso"
    url_lista = "academico:curso_lista"
    mensaje_exito = "Curso registrado correctamente."

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            asignar_matriculas_activas(self.object)
        return response


class CursoUpdateView(FormularioInstitucionalMixin, UpdateView):
    model = Curso
    form_class = CursoForm
    roles_permitidos = ROL_PERSONAL
    titulo = "Editar curso"
    url_lista = "academico:curso_lista"
    mensaje_exito = "Datos del curso actualizados correctamente."


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

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            asignar_cursos_activos(self.object)
        return response


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
                matricula_curso__curso__profesor=self.request.user
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["puede_crear"] = self.request.user.rol == CustomUser.Rol.PROFESOR
        return context


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
                matricula_curso__curso__profesor=self.request.user
            )
        return queryset


class NotaListView(ListaInstitucionalMixin, ListView):
    model = Nota
    titulo = "Notas"
    url_crear = "academico:nota_crear"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.rol == CustomUser.Rol.PROFESOR:
            queryset = queryset.filter(matricula_curso__curso__profesor=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["puede_crear"] = self.request.user.rol == CustomUser.Rol.PROFESOR
        return context


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
            queryset = queryset.filter(matricula_curso__curso__profesor=self.request.user)
        return queryset

class AlertaListView(ListaInstitucionalMixin, ListView):
    model = Alerta
    roles_permitidos = ROLES_ALERTAS
    titulo = "Alertas SAT"
    url_crear = ""
    template_name = "academico/alerta_list.html"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("alumno", "institucion")
        )

        tipo = self.request.GET.get("tipo", "").strip()
        nivel = self.request.GET.get("nivel", "").strip()
        estado = self.request.GET.get("estado", "").strip()
        alumno = self.request.GET.get("alumno", "").strip()

        queryset = queryset.filter(pk__in=alertas_visibles_para(self.request.user))

        if tipo in Alerta.Tipo.values:
            queryset = queryset.filter(tipo=tipo)

        if nivel in Alerta.NivelRiesgo.values:
            queryset = queryset.filter(nivel_riesgo=nivel)

        if estado == "ACTIVA":
            queryset = queryset.filter(activa=True)
        elif estado == "CERRADA":
            queryset = queryset.filter(activa=False)

        if alumno:
            queryset = queryset.filter(
                Q(alumno__dni__icontains=alumno)
                | Q(alumno__nombres__icontains=alumno)
                | Q(alumno__apellidos__icontains=alumno)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "tipos": Alerta.Tipo.choices,
                "niveles": Alerta.NivelRiesgo.choices,
                "tipo": self.request.GET.get("tipo", "").strip(),
                "nivel": self.request.GET.get("nivel", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "alumno": self.request.GET.get("alumno", "").strip(),
                "puede_cerrar": self.request.user.rol in ROLES_CIERRE_ALERTAS,
            }
        )
        return context


@login_required
def alerta_cerrar(request, pk):
    if request.method != "POST":
        raise PermissionDenied("Accion no permitida.")

    if (
        not request.user.is_active
        or request.user.rol not in ROLES_CIERRE_ALERTAS
        or request.user.institucion_id is None
    ):
        raise PermissionDenied("No tiene permiso para cerrar alertas.")

    alerta = get_object_or_404(
        Alerta,
        pk=pk,
        institucion=request.user.institucion,
        activa=True,
    )
    alerta.activa = False
    alerta.save(update_fields=("activa", "fmodificacion"))
    messages.success(request, "Alerta cerrada correctamente.")
    return redirect("academico:alerta_lista")

NIVEL_RIESGO_ORDEN = {
    Alerta.NivelRiesgo.ALTO: 3,
    Alerta.NivelRiesgo.MEDIO: 2,
    Alerta.NivelRiesgo.BAJO: 1,
}

@login_required
def reporte_director(request):
    if not request.user.is_active:
        raise PermissionDenied("No tiene permiso para ver este reporte.")

    instituciones_disponibles = None
    institucion = None

    if request.user.rol == CustomUser.Rol.DIRECTOR:
        institucion = request.user.institucion
    elif request.user.rol == CustomUser.Rol.MINEDU:
        instituciones_disponibles = Institucion.objects.filter(activo=True).order_by("nombre")
        institucion_id = request.GET.get("institucion")
        if institucion_id:
            institucion = get_object_or_404(
                Institucion, pk=institucion_id, activo=True
            )
        else:
            institucion = instituciones_disponibles.first()
    else:
        raise PermissionDenied("No tiene permiso para ver este reporte.")

    if institucion is None:
        return render(
            request,
            "academico/reporte_director.html",
            {
                "instituciones_disponibles": instituciones_disponibles,
                "institucion": None,
                "filas": [],
                "total_alumnos": 0,
                "total_bajo": 0,
                "total_medio": 0,
                "total_alto": 0,
                "total_seguimiento": 0,
            },
        )

    grados = Grado.objects.filter(institucion=institucion, activo=True).order_by(
        "nivel", "nombre", "seccion"
    )

    alertas_activas = Alerta.objects.filter(institucion=institucion, activa=True)
    nivel_por_alumno = {}
    for alerta in alertas_activas.only("alumno_id", "nivel_riesgo"):
        actual = nivel_por_alumno.get(alerta.alumno_id)
        if actual is None or NIVEL_RIESGO_ORDEN[alerta.nivel_riesgo] > NIVEL_RIESGO_ORDEN[actual]:
            nivel_por_alumno[alerta.alumno_id] = alerta.nivel_riesgo

    filas = []
    total_bajo = total_medio = total_alto = 0

    for grado in grados:
        alumnos_ids = Matricula.objects.filter(
            institucion=institucion, grado=grado, estado=Matricula.Estado.ACTIVA
        ).values_list("alumno_id", flat=True)

        bajo = medio = alto = 0
        for alumno_id in alumnos_ids:
            nivel = nivel_por_alumno.get(alumno_id)
            if nivel == Alerta.NivelRiesgo.ALTO:
                alto += 1
            elif nivel == Alerta.NivelRiesgo.MEDIO:
                medio += 1
            else:
                bajo += 1

        filas.append(
            {
                "grado": grado,
                "bajo": bajo,
                "medio": medio,
                "alto": alto,
                "total": bajo + medio + alto,
            }
        )
        total_bajo += bajo
        total_medio += medio
        total_alto += alto

    total_seguimiento = len(nivel_por_alumno)
    total_alumnos = total_bajo + total_medio + total_alto

    return render(
        request,
        "academico/reporte_director.html",
        {
            "instituciones_disponibles": instituciones_disponibles,
            "institucion": institucion,
            "filas": filas,
            "total_bajo": total_bajo,
            "total_medio": total_medio,
            "total_alto": total_alto,
            "total_alumnos": total_alumnos,
            "total_seguimiento": total_seguimiento,
        },
    )

@login_required
def reporte_minedu(request):
    if not request.user.is_active or request.user.rol != CustomUser.Rol.MINEDU:
        raise PermissionDenied("No tiene permiso para ver este reporte.")

    instituciones = Institucion.objects.filter(activo=True).order_by("nombre")

    alertas_activas = Alerta.objects.filter(activa=True)
    nivel_por_alumno = {}
    for alerta in alertas_activas.only("alumno_id", "institucion_id", "nivel_riesgo"):
        clave = (alerta.institucion_id, alerta.alumno_id)
        actual = nivel_por_alumno.get(clave)
        if actual is None or NIVEL_RIESGO_ORDEN[alerta.nivel_riesgo] > NIVEL_RIESGO_ORDEN[actual]:
            nivel_por_alumno[clave] = alerta.nivel_riesgo

    filas = []
    total_bajo = total_medio = total_alto = 0

    for institucion in instituciones:
        alumnos_ids = Matricula.objects.filter(
            institucion=institucion, estado=Matricula.Estado.ACTIVA
        ).values_list("alumno_id", flat=True)

        bajo = medio = alto = 0
        for alumno_id in alumnos_ids:
            nivel = nivel_por_alumno.get((institucion.id, alumno_id))
            if nivel == Alerta.NivelRiesgo.ALTO:
                alto += 1
            elif nivel == Alerta.NivelRiesgo.MEDIO:
                medio += 1
            else:
                bajo += 1

        total = bajo + medio + alto

        if total > 0:
            bajo_pct = bajo / total * 100
            medio_pct = medio / total * 100
            alto_pct = alto / total * 100
            riesgo_final_pct = (medio * 1 + alto * 2) / (total * 2) * 100
        else:
            bajo_pct = medio_pct = alto_pct = riesgo_final_pct = 0

        if riesgo_final_pct >= 50:
            riesgo_final_nivel = Alerta.NivelRiesgo.ALTO
        elif riesgo_final_pct >= 25:
            riesgo_final_nivel = Alerta.NivelRiesgo.MEDIO
        else:
            riesgo_final_nivel = Alerta.NivelRiesgo.BAJO

        filas.append(
            {
                "institucion": institucion,
                "bajo": bajo,
                "medio": medio,
                "alto": alto,
                "total": total,
                "bajo_pct": bajo_pct,
                "medio_pct": medio_pct,
                "alto_pct": alto_pct,
                "riesgo_final_pct": riesgo_final_pct,
                "riesgo_final_nivel": riesgo_final_nivel,
            }
        )
        total_bajo += bajo
        total_medio += medio
        total_alto += alto

    total_alumnos = total_bajo + total_medio + total_alto
    if total_alumnos > 0:
        riesgo_nacional_pct = (total_medio * 1 + total_alto * 2) / (total_alumnos * 2) * 100
    else:
        riesgo_nacional_pct = 0

    if riesgo_nacional_pct >= 50:
        riesgo_nacional_nivel = Alerta.NivelRiesgo.ALTO
    elif riesgo_nacional_pct >= 25:
        riesgo_nacional_nivel = Alerta.NivelRiesgo.MEDIO
    else:
        riesgo_nacional_nivel = Alerta.NivelRiesgo.BAJO

    return render(
        request,
        "academico/reporte_minedu.html",
        {
            "filas": filas,
            "total_bajo": total_bajo,
            "total_medio": total_medio,
            "total_alto": total_alto,
            "total_alumnos": total_alumnos,
            "riesgo_nacional_pct": riesgo_nacional_pct,
            "riesgo_nacional_nivel": riesgo_nacional_nivel,
        },
    )

@login_required
def portal_apoderado(request):
    if not request.user.is_active or request.user.rol != CustomUser.Rol.APODERADO:
        raise PermissionDenied("No tiene permiso para ver este portal.")

    try:
        perfil_apoderado = request.user.perfil_apoderado
    except Apoderado.DoesNotExist:
        perfil_apoderado = None

    hijos = perfil_apoderado.alumnos.all() if perfil_apoderado else Alumno.objects.none()

    return render(request, "academico/portal_apoderado.html", {"hijos": hijos})

def _hijo_de_apoderado_o_403(request, alumno_id):
    if not request.user.is_active or request.user.rol != CustomUser.Rol.APODERADO:
        raise PermissionDenied("No tiene permiso para ver esta seccion.")
    try:
        perfil_apoderado = request.user.perfil_apoderado
    except Apoderado.DoesNotExist:
        raise PermissionDenied("No tiene un perfil de apoderado asociado.")
    alumno = get_object_or_404(perfil_apoderado.alumnos, pk=alumno_id)
    return alumno


@login_required
def portal_apoderado_resumen(request, alumno_id):
    alumno = _hijo_de_apoderado_o_403(request, alumno_id)

    anios = anios_disponibles_alumno(alumno)
    anio = int(request.GET.get("anio", anios[0] if anios else date.today().year))
    bimestre = int(request.GET.get("bimestre", 1))

    rango = obtener_rango_bimestre(anio, bimestre)
    fecha_referencia = rango[0] if rango else date(anio, 1, 1)

    riesgo_asistencia = calcular_riesgo_asistencia(alumno, fecha_referencia)
    riesgo_rendimiento = calcular_riesgo_rendimiento(alumno, fecha_referencia)

    return render(
        request,
        "academico/portal_apoderado_resumen.html",
        {
            "alumno": alumno,
            "anio": anio,
            "bimestre": bimestre,
            "anios": anios,
            "bimestres": [1, 2, 3, 4],
            "riesgo_asistencia": riesgo_asistencia,
            "riesgo_rendimiento": riesgo_rendimiento,
        },
    )

@login_required
def portal_apoderado_notas(request, alumno_id):
    alumno = _hijo_de_apoderado_o_403(request, alumno_id)

    anios = anios_disponibles_alumno(alumno)
    anio = int(request.GET.get("anio", anios[0] if anios else date.today().year))
    bimestre = int(request.GET.get("bimestre", 1))

    datos_por_curso = notas_por_bimestre(alumno, anio, bimestre)

    return render(
        request,
        "academico/portal_apoderado_notas.html",
        {
            "alumno": alumno,
            "anio": anio,
            "bimestre": bimestre,
            "anios": anios,
            "bimestres": [1, 2, 3, 4],
            "datos_por_curso": datos_por_curso,
        },
    )

@login_required
def portal_apoderado_asistencia(request, alumno_id):
    alumno = _hijo_de_apoderado_o_403(request, alumno_id)

    anios = anios_disponibles_alumno(alumno)
    anio = int(request.GET.get("anio", anios[0] if anios else date.today().year))
    bimestre = int(request.GET.get("bimestre", 1))

    meses = calendario_asistencia_bimestre(alumno, anio, bimestre)

    return render(
        request,
        "academico/portal_apoderado_asistencia.html",
        {
            "alumno": alumno,
            "anio": anio,
            "bimestre": bimestre,
            "anios": anios,
            "bimestres": [1, 2, 3, 4],
            "meses": meses,
        },
    )
