from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
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

