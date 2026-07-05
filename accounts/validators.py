from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def normalizar_texto_obligatorio(valor, nombre_campo):
    texto = " ".join((valor or "").split())
    if not texto:
        raise ValidationError(f"{nombre_campo} es obligatorio.")
    return texto


def normalizar_email_obligatorio(valor):
    email = (valor or "").lower().strip()
    if not email:
        raise ValidationError("El correo electronico es obligatorio.")
    validate_email(email)
    return email


def validar_dni_obligatorio(valor):
    dni = (valor or "").strip()
    if not dni:
        raise ValidationError("El DNI es obligatorio.")
    if not dni.isdigit() or len(dni) != 8:
        raise ValidationError("El DNI debe contener exactamente 8 digitos.")
    return dni


def validar_celular_obligatorio(valor):
    celular = (valor or "").strip()
    if not celular:
        raise ValidationError("El celular es obligatorio.")
    if not celular.isdigit() or len(celular) != 9:
        raise ValidationError("El celular debe contener exactamente 9 digitos.")
    return celular


def validar_rol_obligatorio(valor, roles_validos):
    rol = (valor or "").strip()
    if not rol:
        raise ValidationError("El rol es obligatorio.")
    if rol not in roles_validos:
        raise ValidationError("El rol seleccionado no es valido.")
    return rol


def validar_datos_usuario(datos, *, roles_validos=None, requerir_rol=False):
    errores = {}
    normalizados = dict(datos)

    validaciones = {
        "dni": validar_dni_obligatorio,
        "first_name": lambda valor: normalizar_texto_obligatorio(valor, "El nombre"),
        "last_name": lambda valor: normalizar_texto_obligatorio(valor, "Los apellidos"),
        "celular": validar_celular_obligatorio,
        "email": normalizar_email_obligatorio,
    }

    for campo, validador in validaciones.items():
        try:
            normalizados[campo] = validador(datos.get(campo))
        except ValidationError as exc:
            errores[campo] = exc.messages

    if requerir_rol:
        try:
            normalizados["rol"] = validar_rol_obligatorio(
                datos.get("rol"),
                roles_validos or (),
            )
        except ValidationError as exc:
            errores["rol"] = exc.messages

    if errores:
        raise ValidationError(errores)

    return normalizados
