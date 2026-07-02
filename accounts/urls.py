from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    LoginSeguroView,
    activar_cuenta,
    usuario_cambiar_estado,
    usuario_crear,
    usuario_editar,
    usuario_lista,
)

app_name = "accounts"

urlpatterns = [
    path("login/", LoginSeguroView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("activar/<uidb64>/<token>/", activar_cuenta, name="activar_cuenta"),
    path("usuarios/", usuario_lista, name="usuario_lista"),
    path("usuarios/crear/", usuario_crear, name="usuario_crear"),
    path("usuarios/<uuid:codigo_unico>/editar/", usuario_editar, name="usuario_editar"),
    path(
        "usuarios/<uuid:codigo_unico>/estado/",
        usuario_cambiar_estado,
        name="usuario_cambiar_estado",
    ),
]
