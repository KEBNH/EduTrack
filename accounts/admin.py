from django import forms
from django.contrib import admin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser
from .validators import (
    normalizar_email_obligatorio,
    normalizar_texto_obligatorio,
    validar_celular_obligatorio,
    validar_dni_obligatorio,
    validar_rol_obligatorio,
)


class UsuarioAdminValidacionMixin:
    def clean_dni(self):
        return validar_dni_obligatorio(self.cleaned_data["dni"])

    def clean_first_name(self):
        return normalizar_texto_obligatorio(
            self.cleaned_data["first_name"],
            "El nombre",
        )

    def clean_last_name(self):
        return normalizar_texto_obligatorio(
            self.cleaned_data["last_name"],
            "Los apellidos",
        )

    def clean_celular(self):
        return validar_celular_obligatorio(self.cleaned_data["celular"])

    def clean_email(self):
        return normalizar_email_obligatorio(self.cleaned_data["email"])

    def clean_rol(self):
        return validar_rol_obligatorio(
            self.cleaned_data["rol"],
            CustomUser.Rol.values,
        )


class CustomUserAdminForm(UsuarioAdminValidacionMixin, forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = "__all__"


class CustomUserAdminCreationForm(UsuarioAdminValidacionMixin, UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("email", "dni", "first_name", "last_name", "celular", "rol")


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserAdminForm
    add_form = CustomUserAdminCreationForm
    ordering = ("email",)
    list_display = ("email", "dni", "first_name", "last_name", "rol", "is_active")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Datos personales",
            {"fields": ("dni", "first_name", "last_name", "celular", "codigo_unico")},
        ),
        ("EduTrack", {"fields": ("rol", "institucion", "created_by")}),
        (
            "Permisos tecnicos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "date_joined", "fmodificacion")}),
    )
    readonly_fields = ("codigo_unico", "date_joined", "fmodificacion")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "dni",
                    "first_name",
                    "last_name",
                    "celular",
                    "rol",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    search_fields = ("email", "dni", "first_name", "last_name")
