from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailAuthenticationForm
from .views import usuario_cambiar_estado, usuario_crear, usuario_editar, usuario_lista

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("usuarios/", usuario_lista, name="usuario_lista"),
    path("usuarios/crear/", usuario_crear, name="usuario_crear"),
    path("usuarios/<uuid:codigo_unico>/editar/", usuario_editar, name="usuario_editar"),
    path(
        "usuarios/<uuid:codigo_unico>/estado/",
        usuario_cambiar_estado,
        name="usuario_cambiar_estado",
    ),
]
