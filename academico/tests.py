from datetime import date
from io import StringIO
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .forms import ApoderadoForm, AsistenciaForm, MatriculaForm, NotaForm
from .models import (
    Alerta,
    Alumno,
    Asistencia,
    Curso,
    Grado,
    Institucion,
    Matricula,
    MatriculaCurso,
    Nota,
)


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
        )
        self.matricula_curso = MatriculaCurso.objects.create(
            institucion=self.institucion,
            matricula=self.matricula,
            curso=self.curso,
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

    def test_grado_rechaza_tutor_que_no_es_profesor(self):
        self.grado.tutor = self.personal

        with self.assertRaisesMessage(
            ValidationError, "El tutor asignado debe tener el rol Profesor"
        ):
            self.grado.full_clean()

    def test_matricula_asigna_anio_del_grado(self):
        otro_alumno = Alumno.objects.create(
            institucion=self.institucion,
            dni="45678901",
            nombres="Luis",
            apellidos="Rojas",
            fecha_nacimiento=date(2012, 2, 15),
        )
        matricula = Matricula(
            institucion=self.institucion,
            alumno=otro_alumno,
            grado=self.grado,
            anio_academico=2025,
        )

        matricula.full_clean()

        self.assertEqual(matricula.anio_academico, self.grado.anio_academico)

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
        )

        with self.assertRaisesMessage(
            ValidationError, "El alumno debe pertenecer a la misma institucion"
        ):
            matricula.full_clean()

    def test_asistencia_rechaza_curso_matriculado_de_otra_institucion(self):
        asistencia = Asistencia(
            institucion=self.otra_institucion,
            matricula_curso=self.matricula_curso,
            fecha=date(2026, 6, 9),
            estado=Asistencia.Estado.PRESENTE,
        )

        with self.assertRaisesMessage(
            ValidationError, "El curso matriculado debe pertenecer a la misma institucion"
        ):
            asistencia.full_clean()

    def test_asistencia_solo_admite_presente_y_falta(self):
        self.assertEqual(
            Asistencia.Estado.choices,
            [("PRESENTE", "Presente"), ("FALTA", "Falta")],
        )
        asistencia = Asistencia(
            institucion=self.institucion,
            matricula_curso=self.matricula_curso,
            fecha=date(2026, 6, 9),
            estado="TARDANZA",
        )

        with self.assertRaises(ValidationError):
            asistencia.full_clean()

    def test_matricula_curso_rechaza_curso_de_otro_grado(self):
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
        matricula_curso = MatriculaCurso(
            institucion=self.institucion,
            matricula=self.matricula,
            curso=otro_curso,
        )

        with self.assertRaisesMessage(
            ValidationError, "El curso debe pertenecer al grado de la matricula"
        ):
            matricula_curso.full_clean()

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
                "estado": Matricula.Estado.ACTIVA,
            },
            usuario_actual=self.personal,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.institucion, self.institucion)
        self.assertEqual(form.instance.anio_academico, self.grado.anio_academico)

    def test_formulario_nota_rechaza_matricula_retirada(self):
        self.matricula.estado = Matricula.Estado.RETIRADA
        self.matricula.save()
        form = NotaForm(
            {
                "matricula_curso": self.matricula_curso.pk,
                "periodo": Nota.Periodo.PRIMERO,
                "evaluacion": "Practica 1",
                "calificacion": "18.00",
            },
            usuario_actual=self.personal,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("matricula_curso", form.errors)


class FlujoMatriculaCursoTests(TestCase):
    def setUp(self):
        self.institucion = Institucion.objects.create(
            nombre="Colegio Matriculas", codigo="IE-050"
        )
        self.personal = CustomUser.objects.create_user(
            email="personal-matriculas@edutrack.test",
            password="ClaveSegura!2026",
            dni="50123456",
            rol=CustomUser.Rol.PERSONAL_ACADEMICO,
            institucion=self.institucion,
        )
        self.profesor = CustomUser.objects.create_user(
            email="profesor-matriculas@edutrack.test",
            password="ClaveSegura!2026",
            dni="50234567",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        self.alumno = Alumno.objects.create(
            institucion=self.institucion,
            dni="50345678",
            nombres="Lucia",
            apellidos="Torres",
            fecha_nacimiento=date(2012, 5, 4),
        )
        self.grado = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Primero",
            seccion="A",
            anio_academico=2026,
            tutor=self.profesor,
        )
        self.curso_activo = Curso.objects.create(
            institucion=self.institucion,
            nombre="Matematica",
            codigo="MAT-01",
            grado=self.grado,
            profesor=self.profesor,
        )
        self.curso_inactivo = Curso.objects.create(
            institucion=self.institucion,
            nombre="Arte",
            codigo="ART-01",
            grado=self.grado,
            profesor=self.profesor,
            activo=False,
        )

    def test_matricular_asigna_anio_y_cursos_activos_automaticamente(self):
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:matricula_crear"),
            {
                "alumno": self.alumno.pk,
                "grado": self.grado.pk,
                "estado": Matricula.Estado.ACTIVA,
            },
        )

        self.assertRedirects(response, reverse("academico:matricula_lista"))
        matricula = Matricula.objects.get(alumno=self.alumno)
        self.assertEqual(matricula.anio_academico, self.grado.anio_academico)
        self.assertQuerySetEqual(
            matricula.cursos_matriculados.values_list("curso_id", flat=True),
            [self.curso_activo.pk],
        )

    def test_sincronizar_matricula_no_duplica_cursos_existentes(self):
        self.client.force_login(self.personal)
        self.client.post(
            reverse("academico:matricula_crear"),
            {
                "alumno": self.alumno.pk,
                "grado": self.grado.pk,
                "estado": Matricula.Estado.ACTIVA,
            },
        )
        matricula = Matricula.objects.get(alumno=self.alumno)

        self.client.post(
            reverse("academico:matricula_editar", args=[matricula.pk]),
            {
                "alumno": self.alumno.pk,
                "grado": self.grado.pk,
                "estado": Matricula.Estado.ACTIVA,
            },
        )

        self.assertEqual(matricula.cursos_matriculados.count(), 1)

    def test_no_permite_nuevas_asistencias_ni_notas_en_matricula_retirada(self):
        matricula = Matricula.objects.create(
            institucion=self.institucion,
            alumno=self.alumno,
            grado=self.grado,
            estado=Matricula.Estado.RETIRADA,
        )
        matricula_curso = MatriculaCurso.objects.create(
            institucion=self.institucion,
            matricula=matricula,
            curso=self.curso_activo,
        )

        asistencia_form = AsistenciaForm(
            {
                "matricula_curso": matricula_curso.pk,
                "fecha": "2026-06-09",
                "estado": Asistencia.Estado.PRESENTE,
            },
            usuario_actual=self.profesor,
        )
        nota_form = NotaForm(
            {
                "matricula_curso": matricula_curso.pk,
                "periodo": Nota.Periodo.PRIMERO,
                "evaluacion": "Practica 1",
                "calificacion": "18.00",
            },
            usuario_actual=self.profesor,
        )

        self.assertFalse(asistencia_form.is_valid())
        self.assertFalse(nota_form.is_valid())

    def test_asistencia_es_unica_por_alumno_curso_y_fecha(self):
        matricula = Matricula.objects.create(
            institucion=self.institucion,
            alumno=self.alumno,
            grado=self.grado,
        )
        matricula_curso = MatriculaCurso.objects.create(
            institucion=self.institucion,
            matricula=matricula,
            curso=self.curso_activo,
        )
        Asistencia.objects.create(
            institucion=self.institucion,
            matricula_curso=matricula_curso,
            fecha=date(2026, 6, 9),
            estado=Asistencia.Estado.PRESENTE,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Asistencia.objects.create(
                institucion=self.institucion,
                matricula_curso=matricula_curso,
                fecha=date(2026, 6, 9),
                estado=Asistencia.Estado.FALTA,
            )

    def test_profesor_solo_puede_seleccionar_sus_cursos(self):
        otro_profesor = CustomUser.objects.create_user(
            email="otro-profesor-matriculas@edutrack.test",
            password="ClaveSegura!2026",
            dni="50456789",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        otro_curso = Curso.objects.create(
            institucion=self.institucion,
            nombre="Comunicacion",
            codigo="COM-01",
            grado=self.grado,
            profesor=otro_profesor,
        )
        matricula = Matricula.objects.create(
            institucion=self.institucion,
            alumno=self.alumno,
            grado=self.grado,
        )
        curso_propio = MatriculaCurso.objects.create(
            institucion=self.institucion,
            matricula=matricula,
            curso=self.curso_activo,
        )
        curso_ajeno = MatriculaCurso.objects.create(
            institucion=self.institucion,
            matricula=matricula,
            curso=otro_curso,
        )

        asistencia_form = AsistenciaForm(usuario_actual=self.profesor)
        nota_form = NotaForm(usuario_actual=self.profesor)

        self.assertIn(curso_propio, asistencia_form.fields["matricula_curso"].queryset)
        self.assertNotIn(curso_ajeno, asistencia_form.fields["matricula_curso"].queryset)
        self.assertIn(curso_propio, nota_form.fields["matricula_curso"].queryset)
        self.assertNotIn(curso_ajeno, nota_form.fields["matricula_curso"].queryset)


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


class FlujoGradosTests(TestCase):
    def setUp(self):
        self.institucion = Institucion.objects.create(
            nombre="Colegio Grados Uno", codigo="IE-201"
        )
        self.otra_institucion = Institucion.objects.create(
            nombre="Colegio Grados Dos", codigo="IE-202"
        )
        self.personal = CustomUser.objects.create_user(
            email="personal-grados@edutrack.test",
            password="ClaveSegura!2026",
            dni="80123456",
            rol=CustomUser.Rol.PERSONAL_ACADEMICO,
            institucion=self.institucion,
        )
        self.profesor = CustomUser.objects.create_user(
            email="profesor-grados@edutrack.test",
            password="ClaveSegura!2026",
            dni="80234567",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        self.director = CustomUser.objects.create_user(
            email="director-grados@edutrack.test",
            password="ClaveSegura!2026",
            dni="80345678",
            rol=CustomUser.Rol.DIRECTOR,
            institucion=self.institucion,
        )
        self.grado = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Primero",
            seccion="A",
            anio_academico=2026,
        )
        self.grado_externo = Grado.objects.create(
            institucion=self.otra_institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Segundo",
            seccion="B",
            anio_academico=2026,
        )

    def test_personal_crea_grado_y_normaliza_espacios(self):
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:grado_crear"),
            {
                "nivel": Grado.Nivel.PRIMARIA,
                "nombre": "  Tercer   grado ",
                "seccion": " Unica ",
                "anio_academico": 2027,
                "activo": True,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("academico:grado_lista"))
        grado = Grado.objects.get(anio_academico=2027)
        self.assertEqual(grado.institucion, self.institucion)
        self.assertEqual(grado.nombre, "Tercer grado")
        self.assertEqual(grado.seccion, "Unica")
        self.assertContains(response, "Grado registrado correctamente.")

    def test_formulario_rechaza_anio_invalido_y_grado_duplicado(self):
        self.client.force_login(self.personal)
        url = reverse("academico:grado_crear")

        response = self.client.post(
            url,
            {
                "nivel": Grado.Nivel.PRIMARIA,
                "nombre": "Primero",
                "seccion": "A",
                "anio_academico": 999,
                "activo": True,
            },
        )

        self.assertContains(
            response, "El anio academico debe contener exactamente cuatro digitos."
        )

        response = self.client.post(
            url,
            {
                "nivel": self.grado.nivel,
                "nombre": self.grado.nombre,
                "seccion": self.grado.seccion,
                "anio_academico": self.grado.anio_academico,
                "activo": True,
            },
        )

        self.assertContains(
            response,
            "Ya existe este grado y seccion para el anio academico indicado.",
        )

    def test_lista_solo_muestra_grados_de_la_institucion(self):
        self.client.force_login(self.director)

        response = self.client.get(reverse("academico:grado_lista"))

        self.assertContains(response, self.grado.nombre)
        self.assertNotContains(response, self.grado_externo.nombre)
        self.assertNotContains(response, "Nuevo grado")
        self.assertNotContains(
            response, reverse("academico:grado_editar", args=[self.grado.pk])
        )

    def test_lista_busca_y_filtra_grados(self):
        Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.PRIMARIA,
            nombre="Cuarto",
            seccion="C",
            anio_academico=2025,
            activo=False,
        )
        self.client.force_login(self.profesor)

        response = self.client.get(
            reverse("academico:grado_lista"),
            {
                "q": "Cuarto",
                "nivel": Grado.Nivel.PRIMARIA,
                "anio": "2025",
                "estado": "INACTIVO",
            },
        )

        self.assertContains(response, "Cuarto")
        self.assertNotContains(response, self.grado.nombre)

    def test_lista_pagina_diez_grados(self):
        for indice in range(11):
            Grado.objects.create(
                institucion=self.institucion,
                nivel=Grado.Nivel.SECUNDARIA,
                nombre=f"Grado {indice}",
                seccion="A",
                anio_academico=2030 + indice,
            )
        self.client.force_login(self.profesor)

        response = self.client.get(reverse("academico:grado_lista"))

        self.assertEqual(len(response.context["objetos"]), 10)
        self.assertContains(response, "Siguiente")

    def test_profesor_y_director_no_pueden_crear_ni_editar_grados(self):
        for usuario in (self.profesor, self.director):
            self.client.force_login(usuario)
            self.assertEqual(
                self.client.get(reverse("academico:grado_crear")).status_code, 403
            )
            self.assertEqual(
                self.client.get(
                    reverse("academico:grado_editar", args=[self.grado.pk])
                ).status_code,
                403,
            )

    def test_personal_no_puede_editar_grado_de_otra_institucion(self):
        self.client.force_login(self.personal)

        response = self.client.get(
            reverse("academico:grado_editar", args=[self.grado_externo.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_edicion_muestra_mensaje_y_no_detecta_el_mismo_grado_como_duplicado(self):
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:grado_editar", args=[self.grado.pk]),
            {
                "nivel": self.grado.nivel,
                "nombre": self.grado.nombre,
                "seccion": self.grado.seccion,
                "anio_academico": self.grado.anio_academico,
                "activo": False,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("academico:grado_lista"))
        self.grado.refresh_from_db()
        self.assertFalse(self.grado.activo)
        self.assertContains(response, "Datos del grado actualizados correctamente.")


class FlujoCursosTests(TestCase):
    def setUp(self):
        self.institucion = Institucion.objects.create(
            nombre="Colegio Cursos Uno", codigo="IE-301"
        )
        self.otra_institucion = Institucion.objects.create(
            nombre="Colegio Cursos Dos", codigo="IE-302"
        )
        self.personal = CustomUser.objects.create_user(
            email="personal-cursos@edutrack.test",
            password="ClaveSegura!2026",
            dni="90123456",
            rol=CustomUser.Rol.PERSONAL_ACADEMICO,
            institucion=self.institucion,
        )
        self.profesor = CustomUser.objects.create_user(
            email="profesor-cursos@edutrack.test",
            password="ClaveSegura!2026",
            dni="90234567",
            first_name="Pedro",
            last_name="Profesor",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        self.profesor_inactivo = CustomUser.objects.create_user(
            email="profesor-inactivo@edutrack.test",
            password="ClaveSegura!2026",
            dni="90345678",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
            is_active=False,
        )
        self.director = CustomUser.objects.create_user(
            email="director-cursos@edutrack.test",
            password="ClaveSegura!2026",
            dni="90456789",
            rol=CustomUser.Rol.DIRECTOR,
            institucion=self.institucion,
        )
        self.grado = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Primero",
            seccion="A",
            anio_academico=2026,
        )
        self.grado_inactivo = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Segundo",
            seccion="A",
            anio_academico=2026,
            activo=False,
        )
        self.grado_externo = Grado.objects.create(
            institucion=self.otra_institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Primero",
            seccion="B",
            anio_academico=2026,
        )
        self.curso = Curso.objects.create(
            institucion=self.institucion,
            nombre="Matematica",
            codigo="MAT-01",
            grado=self.grado,
            profesor=self.profesor,
        )
        self.curso_externo = Curso.objects.create(
            institucion=self.otra_institucion,
            nombre="Curso externo",
            codigo="EXT-01",
            grado=self.grado_externo,
        )

    def test_personal_crea_curso_y_normaliza_datos(self):
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:curso_crear"),
            {
                "nombre": "  Comunicacion   integral ",
                "codigo": " com-01 ",
                "grado": self.grado.pk,
                "profesor": self.profesor.pk,
                "activo": True,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("academico:curso_lista"))
        curso = Curso.objects.get(codigo="COM-01")
        self.assertEqual(curso.institucion, self.institucion)
        self.assertEqual(curso.nombre, "Comunicacion integral")
        self.assertContains(response, "Curso registrado correctamente.")

    def test_formulario_rechaza_codigo_y_nombre_repetidos_en_el_mismo_grado(self):
        self.client.force_login(self.personal)
        url = reverse("academico:curso_crear")

        response = self.client.post(
            url,
            {
                "nombre": "Curso diferente",
                "codigo": "mat-01",
                "grado": self.grado.pk,
                "profesor": "",
                "activo": True,
            },
        )
        self.assertContains(
            response, "Ya existe un curso con este codigo dentro del grado."
        )

        response = self.client.post(
            url,
            {
                "nombre": "matematica",
                "codigo": "MAT-02",
                "grado": self.grado.pk,
                "profesor": "",
                "activo": True,
            },
        )
        self.assertContains(
            response, "Ya existe un curso con este nombre dentro del grado."
        )

    def test_codigo_y_nombre_pueden_repetirse_en_otro_grado(self):
        otro_grado = Grado.objects.create(
            institucion=self.institucion,
            nivel=Grado.Nivel.SECUNDARIA,
            nombre="Tercero",
            seccion="A",
            anio_academico=2026,
        )
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:curso_crear"),
            {
                "nombre": self.curso.nombre,
                "codigo": self.curso.codigo,
                "grado": otro_grado.pk,
                "profesor": "",
                "activo": True,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("academico:curso_lista"))
        self.assertTrue(Curso.objects.filter(grado=otro_grado).exists())

    def test_base_de_datos_rechaza_duplicados_sin_distinguir_mayusculas(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Curso.objects.create(
                institucion=self.institucion,
                nombre="Curso diferente",
                codigo=self.curso.codigo.lower(),
                grado=self.grado,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Curso.objects.create(
                institucion=self.institucion,
                nombre=self.curso.nombre.lower(),
                codigo="MAT-02",
                grado=self.grado,
            )

    def test_formulario_solo_ofrece_grados_y_profesores_activos_de_la_institucion(self):
        self.client.force_login(self.personal)

        response = self.client.get(reverse("academico:curso_crear"))
        form = response.context["form"]

        self.assertIn(self.grado, form.fields["grado"].queryset)
        self.assertNotIn(self.grado_inactivo, form.fields["grado"].queryset)
        self.assertNotIn(self.grado_externo, form.fields["grado"].queryset)
        self.assertIn(self.profesor, form.fields["profesor"].queryset)
        self.assertNotIn(self.profesor_inactivo, form.fields["profesor"].queryset)

    def test_lista_solo_muestra_cursos_de_la_institucion(self):
        self.client.force_login(self.director)

        response = self.client.get(reverse("academico:curso_lista"))

        self.assertContains(response, self.curso.codigo)
        self.assertNotContains(response, self.curso_externo.codigo)
        self.assertNotContains(response, "Nuevo curso")
        self.assertNotContains(
            response, reverse("academico:curso_editar", args=[self.curso.pk])
        )

    def test_lista_busca_y_filtra_cursos(self):
        curso_inactivo = Curso.objects.create(
            institucion=self.institucion,
            nombre="Historia",
            codigo="HIS-01",
            grado=self.grado,
            profesor=self.profesor,
            activo=False,
        )
        self.client.force_login(self.profesor)

        response = self.client.get(
            reverse("academico:curso_lista"),
            {
                "q": "HIS",
                "grado": str(self.grado.pk),
                "profesor": str(self.profesor.pk),
                "estado": "INACTIVO",
            },
        )

        self.assertContains(response, curso_inactivo.codigo)
        self.assertNotContains(response, self.curso.codigo)

    def test_lista_pagina_diez_cursos(self):
        for indice in range(11):
            Curso.objects.create(
                institucion=self.institucion,
                nombre=f"Curso {indice}",
                codigo=f"CUR-{indice:02d}",
                grado=self.grado,
            )
        self.client.force_login(self.profesor)

        response = self.client.get(reverse("academico:curso_lista"))

        self.assertEqual(len(response.context["objetos"]), 10)
        self.assertContains(response, "Siguiente")

    def test_profesor_y_director_no_pueden_crear_ni_editar_cursos(self):
        for usuario in (self.profesor, self.director):
            self.client.force_login(usuario)
            self.assertEqual(
                self.client.get(reverse("academico:curso_crear")).status_code, 403
            )
            self.assertEqual(
                self.client.get(
                    reverse("academico:curso_editar", args=[self.curso.pk])
                ).status_code,
                403,
            )

    def test_personal_no_puede_editar_curso_de_otra_institucion(self):
        self.client.force_login(self.personal)

        response = self.client.get(
            reverse("academico:curso_editar", args=[self.curso_externo.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_edicion_conserva_relaciones_inactivas_y_muestra_mensaje(self):
        curso_inactivo = Curso.objects.create(
            institucion=self.institucion,
            nombre="Arte",
            codigo="ART-01",
            grado=self.grado_inactivo,
            profesor=self.profesor_inactivo,
        )
        self.client.force_login(self.personal)

        response = self.client.post(
            reverse("academico:curso_editar", args=[curso_inactivo.pk]),
            {
                "nombre": curso_inactivo.nombre,
                "codigo": curso_inactivo.codigo,
                "grado": self.grado_inactivo.pk,
                "profesor": self.profesor_inactivo.pk,
                "activo": False,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("academico:curso_lista"))
        curso_inactivo.refresh_from_db()
        self.assertFalse(curso_inactivo.activo)
        self.assertContains(response, "Datos del curso actualizados correctamente.")

class MotorSATTests(TestCase):
    def setUp(self):
        self.institucion = Institucion.objects.create(
            nombre="Colegio SAT", codigo="IE-SAT"
        )
        self.profesor = CustomUser.objects.create_user(
            email="profesor-sat@edutrack.test",
            password="ClaveSegura!2026",
            dni="11112222",
            rol=CustomUser.Rol.PROFESOR,
            institucion=self.institucion,
        )
        self.alumno = Alumno.objects.create(
            institucion=self.institucion,
            dni="22223333",
            nombres="Valeria",
            apellidos="SAT",
            fecha_nacimiento=date(2012, 3, 10),
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
            codigo="SAT-MAT",
            grado=self.grado,
            profesor=self.profesor,
        )
        self.matricula = Matricula.objects.create(
            institucion=self.institucion,
            alumno=self.alumno,
            grado=self.grado,
        )
        self.matricula_curso = MatriculaCurso.objects.create(
            institucion=self.institucion,
            matricula=self.matricula,
            curso=self.curso,
        )

    def registrar_asistencias(self, estados):
        for indice, estado in enumerate(estados, start=1):
            Asistencia.objects.create(
                institucion=self.institucion,
                matricula_curso=self.matricula_curso,
                fecha=date(2026, 6, indice),
                estado=estado,
            )

    def registrar_nota(self, calificacion, evaluacion="Practica 1"):
        Nota.objects.create(
            institucion=self.institucion,
            matricula_curso=self.matricula_curso,
            periodo=Nota.Periodo.SEGUNDO,
            evaluacion=evaluacion,
            calificacion=calificacion,
        )

    def test_alumno_sin_riesgo_no_genera_alerta(self):
        self.registrar_asistencias(
            [
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
            ]
        )
        self.registrar_nota("16.00")

        from .services import generar_alertas_sat

        generar_alertas_sat(fecha=date(2026, 6, 30))

        self.assertFalse(Alerta.objects.filter(alumno=self.alumno, activa=True).exists())

    def test_faltas_generan_alerta_de_asistencia(self):
        self.registrar_asistencias(
            [
                Asistencia.Estado.FALTA,
                Asistencia.Estado.FALTA,
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
            ]
        )
        self.registrar_nota("16.00")

        from .services import generar_alertas_sat

        generar_alertas_sat(fecha=date(2026, 6, 30))

        alerta = Alerta.objects.get(alumno=self.alumno, tipo=Alerta.Tipo.ASISTENCIA)
        self.assertTrue(alerta.activa)
        self.assertEqual(alerta.nivel_riesgo, Alerta.NivelRiesgo.ALTO)
        self.assertIn("40.00% de faltas", alerta.descripcion)

    def test_notas_bajas_generan_alerta_de_rendimiento(self):
        self.registrar_asistencias(
            [
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
            ]
        )
        self.registrar_nota("12.00")

        from .services import generar_alertas_sat

        generar_alertas_sat(fecha=date(2026, 6, 30))

        alerta = Alerta.objects.get(alumno=self.alumno, tipo=Alerta.Tipo.RENDIMIENTO)
        self.assertTrue(alerta.activa)
        self.assertEqual(alerta.nivel_riesgo, Alerta.NivelRiesgo.ALTO)
        self.assertIn("promedio general 12.00", alerta.descripcion)

    def test_alerta_existente_se_actualiza_y_no_se_duplica(self):
        Alerta.objects.create(
            institucion=self.institucion,
            alumno=self.alumno,
            tipo=Alerta.Tipo.RENDIMIENTO,
            nivel_riesgo=Alerta.NivelRiesgo.MEDIO,
            descripcion="Alerta anterior.",
        )
        self.registrar_nota("11.00")

        from .services import generar_alertas_sat

        generar_alertas_sat(fecha=date(2026, 6, 30))

        alertas = Alerta.objects.filter(
            alumno=self.alumno,
            tipo=Alerta.Tipo.RENDIMIENTO,
            activa=True,
        )
        self.assertEqual(alertas.count(), 1)
        alerta = alertas.get()
        self.assertEqual(alerta.nivel_riesgo, Alerta.NivelRiesgo.ALTO)
        self.assertIn("promedio general 11.00", alerta.descripcion)

    def test_si_riesgo_desaparece_alerta_se_cierra(self):
        Alerta.objects.create(
            institucion=self.institucion,
            alumno=self.alumno,
            tipo=Alerta.Tipo.ASISTENCIA,
            nivel_riesgo=Alerta.NivelRiesgo.ALTO,
            descripcion="Alerta anterior.",
        )
        self.registrar_asistencias(
            [
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
                Asistencia.Estado.PRESENTE,
            ]
        )
        self.registrar_nota("16.00")

        from .services import generar_alertas_sat

        generar_alertas_sat(fecha=date(2026, 6, 30))

        alerta = Alerta.objects.get(alumno=self.alumno, tipo=Alerta.Tipo.ASISTENCIA)
        self.assertFalse(alerta.activa)
        self.assertEqual(alerta.nivel_riesgo, Alerta.NivelRiesgo.BAJO)
    
    def test_comando_generar_alertas_ejecuta_motor_sat(self):
        self.registrar_nota("12.00")
        salida = StringIO()

        call_command("generar_alertas", fecha="2026-06-30", stdout=salida)

        self.assertTrue(
            Alerta.objects.filter(
                alumno=self.alumno,
                tipo=Alerta.Tipo.RENDIMIENTO,
                activa=True,
            ).exists()
        )
        self.assertIn("Motor SAT ejecutado correctamente", salida.getvalue())

    def test_comando_generar_alertas_ignora_fecha_fuera_de_periodo(self):
        self.registrar_nota("12.00")
        salida = StringIO()

        call_command("generar_alertas", fecha="2026-01-15", stdout=salida)

        self.assertFalse(Alerta.objects.filter(alumno=self.alumno).exists())
        self.assertIn("fuera del anio escolar activo", salida.getvalue())