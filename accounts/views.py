from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .forms import ActivarCuentaForm, CustomUserCreationForm, CustomUserUpdateForm
from .models import CustomUser
from .services import (
    crear_usuario,
    enviar_correo_activacion,
    puede_gestionar_usuario,
    roles_permitidos_para,
    usuarios_gestionables_por,
)
from .tokens import activation_token_generator


def _validar_acceso_panel(usuario):
    if not roles_permitidos_para(usuario):
        raise PermissionDenied("No tiene permiso para gestionar usuarios.")


@login_required
def usuario_lista(request):
    _validar_acceso_panel(request.user)
    usuarios = usuarios_gestionables_por(request.user).select_related("institucion")

    consulta = request.GET.get("q", "").strip()
    rol = request.GET.get("rol", "").strip()
    estado = request.GET.get("estado", "").strip()

    if consulta:
        usuarios = usuarios.filter(
            Q(dni__icontains=consulta)
            | Q(first_name__icontains=consulta)
            | Q(last_name__icontains=consulta)
            | Q(email__icontains=consulta)
        )
    if rol in roles_permitidos_para(request.user):
        usuarios = usuarios.filter(rol=rol)
    if estado == "ACTIVO":
        usuarios = usuarios.filter(is_active=True).exclude(password__startswith="!")
    elif estado == "PENDIENTE":
        usuarios = usuarios.filter(is_active=True, password__startswith="!")
    elif estado == "INACTIVO":
        usuarios = usuarios.filter(is_active=False)

    from django.core.paginator import Paginator

    page_obj = Paginator(usuarios.order_by("last_name", "first_name"), 10).get_page(
        request.GET.get("page")
    )
    roles_filtro = [
        choice for choice in request.user.Rol.choices if choice[0] in roles_permitidos_para(request.user)
    ]
    return render(
        request,
        "accounts/user_list.html",
        {
            "page_obj": page_obj,
            "q": consulta,
            "rol": rol,
            "estado": estado,
            "roles_filtro": roles_filtro,
        },
    )


@login_required
def usuario_crear(request):
    _validar_acceso_panel(request.user)

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, usuario_actual=request.user)
        if form.is_valid():
            try:
                usuario = crear_usuario(usuario_actual=request.user, datos=form.cleaned_data)
                enviar_correo_activacion(usuario=usuario, request=request)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    "Usuario creado. Se genero el correo para activar su cuenta.",
                )
                return redirect("accounts:usuario_lista")
    else:
        form = CustomUserCreationForm(usuario_actual=request.user)

    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "titulo": "Crear usuario", "es_creacion": True},
    )


@login_required
def usuario_editar(request, codigo_unico):
    _validar_acceso_panel(request.user)
    usuario = get_object_or_404(usuarios_gestionables_por(request.user), codigo_unico=codigo_unico)
    if not puede_gestionar_usuario(request.user, usuario):
        raise PermissionDenied("No tiene permiso para editar este usuario.")

    if request.method == "POST":
        form = CustomUserUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos del usuario actualizados.")
            return redirect("accounts:usuario_lista")
    else:
        form = CustomUserUpdateForm(instance=usuario)
    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "titulo": "Editar usuario", "usuario_objetivo": usuario},
    )


@login_required
def usuario_cambiar_estado(request, codigo_unico):
    if request.method != "POST":
        raise PermissionDenied("Accion no permitida.")

    _validar_acceso_panel(request.user)
    usuario = get_object_or_404(usuarios_gestionables_por(request.user), codigo_unico=codigo_unico)
    if not puede_gestionar_usuario(request.user, usuario):
        raise PermissionDenied("No tiene permiso para cambiar el estado de este usuario.")

    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=("is_active", "fmodificacion"))
    messages.success(request, "Estado del usuario actualizado.")
    return redirect("accounts:usuario_lista")


def activar_cuenta(request, uidb64, token):
    try:
        usuario_id = force_str(urlsafe_base64_decode(uidb64))
        usuario = CustomUser.objects.get(pk=usuario_id)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        usuario = None

    token_valido = (
        usuario is not None
        and usuario.is_active
        and not usuario.has_usable_password()
        and activation_token_generator.check_token(usuario, token)
    )
    if not token_valido:
        return render(request, "accounts/activate.html", {"enlace_invalido": True})

    if request.method == "POST":
        form = ActivarCuentaForm(usuario, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta activada. Ya puede iniciar sesion.")
            return redirect("accounts:login")
    else:
        form = ActivarCuentaForm(usuario)

    return render(request, "accounts/activate.html", {"form": form})
