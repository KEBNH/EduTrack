from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from academico.models import Institucion

from .models import CustomUser
from .tokens import activation_token_generator


ROLES_QUE_PUEDE_CREAR = {
    CustomUser.Rol.IT: {CustomUser.Rol.MINEDU},
    CustomUser.Rol.MINEDU: {CustomUser.Rol.DIRECTOR},
    CustomUser.Rol.DIRECTOR: {
        CustomUser.Rol.PROFESOR,
        CustomUser.Rol.PERSONAL_ACADEMICO,
    },
CustomUser.Rol.PERSONAL_ACADEMICO: {CustomUser.Rol.APODERADO},
}

ROLES_GESTION_LIMITADA_POR_INSTITUCION = {
    CustomUser.Rol.DIRECTOR,
    CustomUser.Rol.PERSONAL_ACADEMICO,
}

ROLES_CON_INSTITUCION = {
    CustomUser.Rol.DIRECTOR,
    CustomUser.Rol.PROFESOR,
    CustomUser.Rol.PERSONAL_ACADEMICO,
    CustomUser.Rol.APODERADO,
}

CAPACIDADES_POR_ROL = {
    CustomUser.Rol.IT: [
        "Crear y gestionar usuarios empleados del MINEDU.",
        "Supervisar el acceso inicial de los usuarios del sistema.",
    ],
    CustomUser.Rol.MINEDU: [
        "Crear y gestionar usuarios con rol Director.",
        "Asignar directores a la institucion educativa activa.",
    ],
    CustomUser.Rol.DIRECTOR: [
        "Crear y gestionar profesores y personal academico de su institucion.",
        "Consultar alumnos, apoderados, grados, cursos, matriculas, asistencias y notas.",
    ],
    CustomUser.Rol.PROFESOR: [
        "Consultar la informacion academica de su institucion.",
        "Registrar y actualizar asistencias y notas de sus cursos.",
    ],
    CustomUser.Rol.PERSONAL_ACADEMICO: [
        "Gestionar alumnos, apoderados, grados, cursos y matriculas.",
        "Registrar y actualizar asistencias y notas.",
    ],
    CustomUser.Rol.APODERADO: [
        "Actualmente no tiene modulos de consulta habilitados.",
    ],
}


def puede_crear_usuario(usuario_actual, rol_objetivo):
    if not usuario_actual.is_authenticated or not usuario_actual.is_active:
        return False
    return rol_objetivo in ROLES_QUE_PUEDE_CREAR.get(usuario_actual.rol, set())


def roles_permitidos_para(usuario_actual):
    return ROLES_QUE_PUEDE_CREAR.get(usuario_actual.rol, set())


def capacidades_para(usuario_actual):
    return CAPACIDADES_POR_ROL.get(usuario_actual.rol, [])


def puede_gestionar_usuario(usuario_actual, usuario_objetivo):
    if not usuario_actual.is_authenticated or not usuario_actual.is_active:
        return False
    if usuario_objetivo.rol not in roles_permitidos_para(usuario_actual):
        return False
    if usuario_actual.rol in ROLES_GESTION_LIMITADA_POR_INSTITUCION:
        return usuario_objetivo.institucion_id == usuario_actual.institucion_id
    return True


def usuarios_gestionables_por(usuario_actual):
    roles = roles_permitidos_para(usuario_actual)
    if not roles:
        return CustomUser.objects.none()

    usuarios = CustomUser.objects.filter(rol__in=roles)
    if usuario_actual.rol in ROLES_GESTION_LIMITADA_POR_INSTITUCION:
        usuarios = usuarios.filter(institucion=usuario_actual.institucion)
    return usuarios


def determinar_institucion_usuario(usuario_actual, rol_objetivo):
    if rol_objetivo not in ROLES_CON_INSTITUCION:
        return None

    if usuario_actual.rol == CustomUser.Rol.MINEDU:
        instituciones = Institucion.objects.filter(activo=True)
        if instituciones.count() != 1:
            raise ValidationError(
                "Debe existir exactamente una institucion activa para crear un Director."
            )
        return instituciones.first()

    if not usuario_actual.institucion_id:
        raise ValidationError("El usuario creador no tiene una institucion asignada.")
    return usuario_actual.institucion


@transaction.atomic
def crear_usuario(*, usuario_actual, datos):
    rol_objetivo = datos["rol"]
    if not puede_crear_usuario(usuario_actual, rol_objetivo):
        raise PermissionDenied("No tiene permiso para crear usuarios con este rol.")

    usuario = CustomUser(
        email=datos["email"],
        dni=datos["dni"],
        first_name=datos["first_name"],
        last_name=datos["last_name"],
        celular=datos.get("celular", ""),
        rol=rol_objetivo,
        institucion=determinar_institucion_usuario(usuario_actual, rol_objetivo),
        created_by=usuario_actual,
    )
    usuario.set_unusable_password()
    usuario.save()
    return usuario


def enviar_correo_activacion(*, usuario, request):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = activation_token_generator.make_token(usuario)
    activation_url = request.build_absolute_uri(
        reverse("accounts:activar_cuenta", kwargs={"uidb64": uid, "token": token})
    )
    contexto = {"usuario": usuario, "activation_url": activation_url}
    asunto = render_to_string(
        "accounts/activation_email_subject.txt", contexto
    ).strip()
    mensaje = render_to_string("accounts/activation_email.txt", contexto)
    send_mail(asunto, mensaje, None, [usuario.email])