import re

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.urls import reverse

from academico.models import Institucion

from .models import CustomUser
from .services import (
    crear_usuario,
    puede_crear_usuario,
    puede_gestionar_usuario,
    roles_permitidos_para,
    usuarios_gestionables_por,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    LOGIN_MAX_ATTEMPTS=3,
    LOGIN_LOCKOUT_SECONDS=600,
)
class LoginSeguroTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = CustomUser.objects.create_user(
            email="login@edutrack.test",
            password="ClaveSegura!2026",
            dni="11112222",
            rol=CustomUser.Rol.IT,
        )

    def login(self, email="login@edutrack.test", password="ClaveSegura!2026"):
        return self.client.post(
            reverse("accounts:login"),
            {"username": email, "password": password},
        )

    def test_login_correcto_normaliza_correo(self):
        response = self.login(email=" LOGIN@EDUTRACK.TEST ")

        self.assertRedirects(response, reverse("inicio"))

    def test_login_incorrecto_muestra_mensaje_generico(self):
        response = self.login(password="clave-incorrecta")

        self.assertContains(response, "Correo o contrasena invalidos.")
        self.assertNotContains(response, "no existe")
        self.assertNotContains(response, "inactiva")

    def test_bloquea_temporalmente_despues_de_intentos_fallidos(self):
        for _ in range(3):
            self.login(password="clave-incorrecta")

        response = self.login()

        self.assertContains(
            response,
            "Demasiados intentos fallidos. Intente nuevamente en unos minutos.",
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_inactivo_no_puede_iniciar_sesion(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=("is_active",))

        response = self.login()

        self.assertContains(response, "Correo o contrasena invalidos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_pendiente_no_puede_iniciar_sesion(self):
        pendiente = CustomUser.objects.create_user(
            email="pendiente@edutrack.test",
            password="Temporal!2026",
            dni="22223333",
            rol=CustomUser.Rol.MINEDU,
        )
        pendiente.set_unusable_password()
        pendiente.save(update_fields=("password",))

        response = self.login(
            email="pendiente@edutrack.test",
            password="Temporal!2026",
        )

        self.assertContains(response, "Correo o contrasena invalidos.")
        self.assertNotIn("_auth_user_id", self.client.session)


class ConfiguracionSesionTests(TestCase):
    def test_sesion_expira_tras_quince_minutos_de_inactividad(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 900)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    LOGIN_MAX_ATTEMPTS=3,
    LOGIN_LOCKOUT_SECONDS=600,
)
class LoginSeguroTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = CustomUser.objects.create_user(
            email="login@edutrack.test",
            password="ClaveSegura!2026",
            dni="11112222",
            rol=CustomUser.Rol.IT,
        )

    def login(self, email="login@edutrack.test", password="ClaveSegura!2026"):
        return self.client.post(
            reverse("accounts:login"),
            {"username": email, "password": password},
        )

    def test_login_correcto_normaliza_correo(self):
        response = self.login(email=" LOGIN@EDUTRACK.TEST ")

        self.assertRedirects(response, reverse("inicio"))

    def test_login_incorrecto_muestra_mensaje_generico(self):
        response = self.login(password="clave-incorrecta")

        self.assertContains(response, "Correo o contrasena invalidos.")
        self.assertNotContains(response, "no existe")
        self.assertNotContains(response, "inactiva")

    def test_bloquea_temporalmente_despues_de_intentos_fallidos(self):
        for _ in range(3):
            self.login(password="clave-incorrecta")

        response = self.login()

        self.assertContains(
            response,
            "Demasiados intentos fallidos. Intente nuevamente en unos minutos.",
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_inactivo_no_puede_iniciar_sesion(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=("is_active",))

        response = self.login()

        self.assertContains(response, "Correo o contrasena invalidos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_pendiente_no_puede_iniciar_sesion(self):
        pendiente = CustomUser.objects.create_user(
            email="pendiente@edutrack.test",
            password="Temporal!2026",
            dni="22223333",
            rol=CustomUser.Rol.MINEDU,
        )
        pendiente.set_unusable_password()
        pendiente.save(update_fields=("password",))

        response = self.login(
            email="pendiente@edutrack.test",
            password="Temporal!2026",
        )

        self.assertContains(response, "Correo o contrasena invalidos.")
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class FlujoActivacionTests(TestCase):
    def setUp(self):
        self.usuario_it = CustomUser.objects.create_user(
            email="it@edutrack.test",
            password="ClaveSegura!2026",
            dni="12345678",
            first_name="Kevin",
            last_name="Moreyra",
            rol=CustomUser.Rol.IT,
        )
        self.client.force_login(self.usuario_it)

    def crear_usuario_pendiente(self):
        response = self.client.post(
            reverse("accounts:usuario_crear"),
            {
                "dni": "87654321",
                "first_name": "Maria",
                "last_name": "Perez",
                "celular": "987654321",
                "email": "maria@edutrack.test",
                "rol": CustomUser.Rol.MINEDU,
            },
        )
        self.assertRedirects(response, reverse("accounts:usuario_lista"))
        return CustomUser.objects.get(email="maria@edutrack.test")

    def test_usuario_nuevo_queda_pendiente_y_recibe_correo(self):
        usuario = self.crear_usuario_pendiente()

        self.assertEqual(usuario.estado_cuenta, "PENDIENTE")
        self.assertEqual(usuario.estado_cuenta_display, "Activación pendiente")
        self.assertFalse(usuario.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Activa tu cuenta", mail.outbox[0].subject)
        self.assertIn("/accounts/activar/", mail.outbox[0].body)

    def test_enlace_activa_cuenta_y_no_puede_reutilizarse(self):
        usuario = self.crear_usuario_pendiente()
        activation_url = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
        activation_path = activation_url.removeprefix("http://testserver")

        response = self.client.post(
            activation_path,
            {
                "new_password1": "NuevaClave!2026",
                "new_password2": "NuevaClave!2026",
            },
        )

        self.assertRedirects(response, reverse("accounts:login"))
        usuario.refresh_from_db()
        self.assertEqual(usuario.estado_cuenta, "ACTIVO")
        self.assertTrue(usuario.check_password("NuevaClave!2026"))

        response = self.client.get(activation_path)
        self.assertContains(response, "El enlace de activacion no es valido")

    def test_dashboard_muestra_usuario_rol_y_capacidades(self):
        response = self.client.get(reverse("inicio"))

        self.assertContains(response, "Kevin Moreyra")
        self.assertContains(response, "IT / Soporte Tecnico")
        self.assertContains(response, "Crear y gestionar usuarios empleados del MINEDU.")
        self.assertNotContains(response, "Kevin M.")

    def test_lista_muestra_estado_sin_exponer_uuid(self):
        usuario = self.crear_usuario_pendiente()

        response = self.client.get(reverse("accounts:usuario_lista"))

        self.assertContains(response, "Activación pendiente")
        self.assertNotContains(response, f"<td>{usuario.codigo_unico}</td>", html=True)


class PermisosCreacionUsuariosTests(TestCase):
    def setUp(self):
        self.institucion = Institucion.objects.create(
            nombre="IE Central",
            codigo="IE-001",
        )
        self.otra_institucion = Institucion.objects.create(
            nombre="IE Norte",
            codigo="IE-002",
        )
        self.personal = CustomUser.objects.create_user(
            email="personal@edutrack.test",
            password="ClaveSegura!2026",
            dni="33334444",
            rol=CustomUser.Rol.PERSONAL_ACADEMICO,
            institucion=self.institucion,
        )
        self.profesor = CustomUser.objects.create_user(
            email="profesor@edutrack.test",
            password="ClaveSegura!2026",
            dni="44445555",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        self.director = CustomUser.objects.create_user(
            email="director@edutrack.test",
            password="ClaveSegura!2026",
            dni="55556666",
            rol=CustomUser.Rol.DIRECTOR,
            institucion=self.institucion,
        )

    