from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .forms import ApoderadoForm, MatriculaForm, NotaForm
from .models import Alerta, Alumno, Asistencia, Curso, Grado, Institucion, Matricula, Nota


class IntegridadAcademicaTests(TestCase):
    def setUp(self):
        self.institucion = Institucion.objects.create(
            nombre="Colegio Uno", codigo="IE-001"
        )
        self.otra_institucion = Institucion.objects.create(
            nombre="Colegio Dos", codigo="IE-002"
        )
        self.personal = CustomUser.objects.create_user(
            email="personal@edutrack.test",
            password="ClaveSegura!2026",
            dni="12345678",
            rol=CustomUser.Rol.PERSONAL_ACADEMICO,
            institucion=self.institucion,
        )
        self.profesor = CustomUser.objects.create_user(
            email="profesor@edutrack.test",
            password="ClaveSegura!2026",
            dni="23456789",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        self.alumno = Alumno.objects.create(
            institucion=self.institucion,
            dni="34567890",
            nombres="Ana",
            apellidos="Perez",
            fecha_nacimiento=date(2012, 1, 10),
        )
        self.grado = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Primero",
            seccion="A",
            anio_academico=2026,
        )
        self.curso = Curso.objects.create(
            institucion=self.institucion,
            nombre="Matematica",
            codigo="MAT-01",
            grado=self.grado,
            profesor=self.profesor,
        )
        self.matricula = Matricula.objects.create(
            institucion=self.institucion,
            alumno=self.alumno,
            grado=self.grado,
            anio_academico=2026,
        )

    def test_curso_rechaza_grado_de_otra_institucion(self):
        grado_externo = Grado.objects.create(
            institucion=self.otra_institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Primero",
            seccion="A",
            anio_academico=2026,
        )
        curso = Curso(
            institucion=self.institucion,
            nombre="Comunicacion",
            codigo="COM-01",
            grado=grado_externo,
        )

        with self.assertRaisesMessage(
            ValidationError, "El grado debe pertenecer a la misma institucion"
        ):
            curso.full_clean()

    def test_curso_rechaza_usuario_que_no_es_profesor(self):
        curso = Curso(
            institucion=self.institucion,
            nombre="Comunicacion",
            codigo="COM-01",
            grado=self.grado,
            profesor=self.personal,
        )

        with self.assertRaisesMessage(
            ValidationError, "El usuario asignado debe tener el rol Profesor"
        ):
            curso.full_clean()

    def test_matricula_rechaza_anio_distinto_al_grado(self):
        matricula = Matricula(
            institucion=self.institucion,
            alumno=self.alumno,
            grado=self.grado,
            anio_academico=2025,
        )

        with self.assertRaisesMessage(
            ValidationError, "El anio academico debe coincidir con el anio del grado"
        ):
            matricula.full_clean()

    def test_matricula_rechaza_alumno_de_otra_institucion(self):
        alumno_externo = Alumno.objects.create(
            institucion=self.otra_institucion,
            dni="45678901",
            nombres="Carlos",
            apellidos="Ruiz",
            fecha_nacimiento=date(2012, 3, 20),
        )
        matricula = Matricula(
            institucion=self.institucion,
            alumno=alumno_externo,
            grado=self.grado,
            anio_academico=2026,
        )

        with self.assertRaisesMessage(
            ValidationError, "El alumno debe pertenecer a la misma institucion"
        ):
            matricula.full_clean()

    def test_asistencia_rechaza_matricula_de_otra_institucion(self):
        asistencia = Asistencia(
            institucion=self.otra_institucion,
            matricula=self.matricula,
            fecha=date(2026, 6, 9),
            estado=Asistencia.Estado.PRESENTE,
        )

        with self.assertRaisesMessage(
            ValidationError, "La matricula debe pertenecer a la misma institucion"
        ):
            asistencia.full_clean()

    def test_nota_rechaza_curso_de_otro_grado(self):
        otro_grado = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Segundo",
            seccion="A",
            anio_academico=2026,
        )
        otro_curso = Curso.objects.create(
            institucion=self.institucion,
            nombre="Comunicacion",
            codigo="COM-02",
            grado=otro_grado,
            profesor=self.profesor,
        )
        nota = Nota(
            institucion=self.institucion,
            matricula=self.matricula,
            curso=otro_curso,
            periodo=Nota.Periodo.PRIMERO,
            evaluacion="Practica 1",
            calificacion=Decimal("18.00"),
        )

        with self.assertRaisesMessage(
            ValidationError, "El curso debe pertenecer al grado de la matricula"
        ):
            nota.full_clean()

    def test_alerta_rechaza_alumno_de_otra_institucion(self):
        alerta = Alerta(
            institucion=self.otra_institucion,
            alumno=self.alumno,
            tipo=Alerta.Tipo.ASISTENCIA,
            nivel_riesgo=Alerta.NivelRiesgo.ALTO,
            descripcion="Ausencias reiteradas.",
        )

        with self.assertRaisesMessage(
            ValidationError, "El alumno debe pertenecer a la misma institucion"
        ):
            alerta.full_clean()

    def test_formulario_apoderado_rechaza_alumno_de_otra_institucion(self):
        alumno_externo = Alumno.objects.create(
            institucion=self.otra_institucion,
            dni="56789012",
            nombres="Sofia",
            apellidos="Diaz",
            fecha_nacimiento=date(2012, 4, 5),
        )
        form = ApoderadoForm(
            {
                "dni": "67890123",
                "nombres": "Elena",
                "apellidos": "Diaz",
                "celular": "987654321",
                "correo": "elena@edutrack.test",
                "parentesco": "MADRE",
                "alumnos": [alumno_externo.pk],
                "activo": True,
            },
            usuario_actual=self.personal,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("alumnos", form.errors)

    def test_formulario_matricula_asigna_institucion_antes_de_validar(self):
        otro_alumno = Alumno.objects.create(
            institucion=self.institucion,
            dni="45678901",
            nombres="Luis",
            apellidos="Rojas",
            fecha_nacimiento=date(2012, 2, 15),
        )
        form = MatriculaForm(
            {
                "alumno": otro_alumno.pk,
                "grado": self.grado.pk,
                "anio_academico": 2026,
                "estado": Matricula.Estado.ACTIVA,
            },
            usuario_actual=self.personal,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.institucion, self.institucion)

    def test_formulario_nota_rechaza_curso_de_otro_grado(self):
        otro_grado = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Segundo",
            seccion="B",
            anio_academico=2026,
        )
        otro_curso = Curso.objects.create(
            institucion=self.institucion,
            nombre="Historia",
            codigo="HIS-02",
            grado=otro_grado,
            profesor=self.profesor,
        )
        form = NotaForm(
            {
                "matricula": self.matricula.pk,
                "curso": otro_curso.pk,
                "periodo": Nota.Periodo.PRIMERO,
                "evaluacion": "Practica 1",
                "calificacion": "18.00",
            },
            usuario_actual=self.personal,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("curso", form.errors)


class FlujoAlumnosTests(TestCase):
    def setUp(self):
        self.institucion = Institucion.objects.create(
            nombre="Colegio Uno", codigo="IE-101"
        )
        self.otra_institucion = Institucion.objects.create(
            nombre="Colegio Dos", codigo="IE-102"
        )
        self.personal = CustomUser.objects.create_user(
            email="personal-alumnos@edutrack.test",
            password="ClaveSegura!2026",
            dni="70123456",
            rol=CustomUser.Rol.PERSONAL_ACADEMICO,
            institucion=self.institucion,
        )
        self.profesor = CustomUser.objects.create_user(
            email="profesor-alumnos@edutrack.test",
            password="ClaveSegura!2026",
            dni="70234567",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        self.director = CustomUser.objects.create_user(
            email="director-alumnos@edutrack.test",
            password="ClaveSegura!2026",
            dni="70345678",
            rol=CustomUser.Rol.DIRECTOR,
            institucion=self.institucion,
        )
        self.alumno = Alumno.objects.create(
            institucion=self.institucion,
            dni="70456789",
            nombres="Ana",
            apellidos="Perez",
            fecha_nacimiento=date(2012, 5, 10),
        )
        self.alumno_externo = Alumno.objects.create(
            institucion=self.otra_institucion,
            dni="70567890",
            nombres="Mario",
            apellidos="Externo",
            fecha_nacimiento=date(2011, 8, 20),
        )

    def test_personal_crea_alumno_y_normaliza_espacios(self):
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:alumno_crear"),
            {
                "dni": "70678901",
                "nombres": "  Maria   Elena ",
                "apellidos": " De la   Cruz ",
                "fecha_nacimiento": "2013-02-15",
                "activo": True,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("academico:alumno_lista"))
        alumno = Alumno.objects.get(dni="70678901")
        self.assertEqual(alumno.institucion, self.institucion)
        self.assertEqual(alumno.nombres, "Maria Elena")
        self.assertEqual(alumno.apellidos, "De la Cruz")
        self.assertContains(response, "Alumno registrado correctamente.")

    def test_formulario_rechaza_dni_invalido_fecha_futura_y_duplicado(self):
        self.client.force_login(self.personal)
        url = reverse("academico:alumno_crear")

        response = self.client.post(
            url,
            {
                "dni": "ABC123",
                "nombres": "Luisa",
                "apellidos": "Ramos",
                "fecha_nacimiento": "2099-01-01",
                "activo": True,
            },
        )

        self.assertContains(response, "El DNI debe contener exactamente 8 digitos.")
        self.assertContains(response, "La fecha de nacimiento no puede ser futura.")

        response = self.client.post(
            url,
            {
                "dni": self.alumno.dni,
                "nombres": "Otra",
                "apellidos": "Persona",
                "fecha_nacimiento": "2012-01-01",
                "activo": True,
            },
        )

        self.assertContains(
            response, "Ya existe un alumno con este DNI en la institucion."
        )

    def test_lista_solo_muestra_alumnos_de_la_institucion(self):
        self.client.force_login(self.director)

        response = self.client.get(reverse("academico:alumno_lista"))

        self.assertContains(response, self.alumno.dni)
        self.assertNotContains(response, self.alumno_externo.dni)
        self.assertNotContains(response, "Nuevo alumno")
        self.assertNotContains(
            response, reverse("academico:alumno_editar", args=[self.alumno.pk])
        )

    def test_lista_busca_y_filtra_por_estado(self):
        Alumno.objects.create(
            institucion=self.institucion,
            dni="70789012",
            nombres="Carlos",
            apellidos="Inactivo",
            fecha_nacimiento=date(2012, 7, 10),
            activo=False,
        )
        self.client.force_login(self.profesor)

        response = self.client.get(
            reverse("academico:alumno_lista"), {"q": "Carlos", "estado": "INACTIVO"}
        )

        self.assertContains(response, "70789012")
        self.assertNotContains(response, self.alumno.dni)

    def test_lista_pagina_diez_alumnos(self):
        for indice in range(11):
            Alumno.objects.create(
                institucion=self.institucion,
                dni=f"8{indice:07d}",
                nombres=f"Alumno {indice}",
                apellidos="Paginado",
                fecha_nacimiento=date(2012, 1, 1),
            )
        self.client.force_login(self.profesor)

        response = self.client.get(reverse("academico:alumno_lista"))

        self.assertEqual(len(response.context["objetos"]), 10)
        self.assertContains(response, "Siguiente")

    def test_profesor_y_director_no_pueden_crear_ni_editar(self):
        for usuario in (self.profesor, self.director):
            self.client.force_login(usuario)
            self.assertEqual(
                self.client.get(reverse("academico:alumno_crear")).status_code, 403
            )
            self.assertEqual(
                self.client.get(
                    reverse("academico:alumno_editar", args=[self.alumno.pk])
                ).status_code,
                403,
            )

    def test_personal_no_puede_editar_alumno_de_otra_institucion(self):
        self.client.force_login(self.personal)

        response = self.client.get(
            reverse("academico:alumno_editar", args=[self.alumno_externo.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_edicion_muestra_mensaje_y_conserva_dni_del_mismo_alumno(self):
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:alumno_editar", args=[self.alumno.pk]),
            {
                "dni": self.alumno.dni,
                "nombres": "Ana Maria",
                "apellidos": self.alumno.apellidos,
                "fecha_nacimiento": self.alumno.fecha_nacimiento.isoformat(),
                "activo": True,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("academico:alumno_lista"))
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.nombres, "Ana Maria")
        self.assertContains(response, "Datos del alumno actualizados correctamente.")
