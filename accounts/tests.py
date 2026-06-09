import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CustomUser


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
