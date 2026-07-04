from datetime import date

from django import forms
from django.db.models import Q

from accounts.models import CustomUser

from .models import (
    Alumno,
    Apoderado,
    Asistencia,
    Curso,
    Grado,
    Matricula,
    MatriculaCurso,
    Nota,
)


class FormularioInstitucional(forms.ModelForm):
    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_actual = usuario_actual
        if usuario_actual and usuario_actual.institucion_id:
            self.instance.institucion = usuario_actual.institucion
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class AlumnoForm(FormularioInstitucional):
    class Meta:
        model = Alumno
        fields = ("dni", "nombres", "apellidos", "fecha_nacimiento", "activo")
        labels = {"fecha_nacimiento": "Fecha de nacimiento"}
        help_texts = {"dni": "Ingrese exactamente 8 digitos."}
        widgets = {
            "dni": forms.TextInput(
                attrs={"inputmode": "numeric", "maxlength": "8", "autocomplete": "off"}
            ),
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_dni(self):
        dni = self.cleaned_data["dni"].strip()
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe contener exactamente 8 digitos.")
        if self.instance.institucion_id and Alumno.objects.filter(
            institucion_id=self.instance.institucion_id, dni=dni
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                "Ya existe un alumno con este DNI en la institucion."
            )
        return dni

    def clean_nombres(self):
        return " ".join(self.cleaned_data["nombres"].split())

    def clean_apellidos(self):
        return " ".join(self.cleaned_data["apellidos"].split())

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data["fecha_nacimiento"]
        if fecha_nacimiento > date.today():
            raise forms.ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha_nacimiento


class ApoderadoForm(FormularioInstitucional):
    class Meta:
        model = Apoderado
        fields = (
            "dni",
            "nombres",
            "apellidos",
            "celular",
            "correo",
            "parentesco",
            "alumnos",
            "activo",
        )
        widgets = {"alumnos": forms.SelectMultiple(attrs={"class": "form-select"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.usuario_actual and self.usuario_actual.institucion_id:
            self.fields["alumnos"].queryset = Alumno.objects.filter(
                institucion=self.usuario_actual.institucion
            )
        else:
            self.fields["alumnos"].queryset = Alumno.objects.none()

    def clean_alumnos(self):
        alumnos = self.cleaned_data["alumnos"]
        if self.usuario_actual and alumnos.exclude(
            institucion=self.usuario_actual.institucion
        ).exists():
            raise forms.ValidationError(
                "Todos los alumnos deben pertenecer a la institucion del apoderado."
            )
        return alumnos


class InscripcionForm(forms.Form):
    apoderado_usuario = forms.ModelChoiceField(
        label="Apoderado",
        queryset=CustomUser.objects.none(),
        help_text=(
            "Seleccione un usuario con rol Padre/Apoderado. "
            "Si no aparece, debe crearlo primero en Usuarios."
        ),
    )

    alumno_dni = forms.CharField(
        label="DNI del alumno",
        max_length=8,
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "maxlength": "8", "autocomplete": "off"}
        ),
    )
    alumno_nombres = forms.CharField(label="Nombres del alumno", max_length=150)
    alumno_apellidos = forms.CharField(label="Apellidos del alumno", max_length=150)
    alumno_fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento del alumno",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    grado = forms.ModelChoiceField(label="Grado", queryset=Grado.objects.none())

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_actual = usuario_actual
        institucion = getattr(usuario_actual, "institucion", None)
        self.fields["apoderado_usuario"].queryset = CustomUser.objects.filter(
            institucion=institucion,
            rol=CustomUser.Rol.APODERADO,
            is_active=True,
        ).order_by("last_name", "first_name", "email")
        self.fields["grado"].queryset = Grado.objects.filter(
            institucion=institucion, activo=True
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def _validar_dni(self, campo):
        dni = self.cleaned_data[campo].strip()
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe contener exactamente 8 digitos.")
        return dni

    def _validar_celular(self, campo):
        celular = self.cleaned_data[campo].strip()
        if not celular.isdigit() or len(celular) != 9:
            raise forms.ValidationError(
                "El celular debe contener exactamente 9 digitos."
            )
        return celular

    def clean_apoderado_dni(self):
        return self._validar_dni("apoderado_dni")

    def clean_alumno_dni(self):
        return self._validar_dni("alumno_dni")

    def clean_alumno_nombres(self):
        return " ".join(self.cleaned_data["alumno_nombres"].split())

    def clean_alumno_apellidos(self):
        return " ".join(self.cleaned_data["alumno_apellidos"].split())

    def clean_alumno_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data["alumno_fecha_nacimiento"]
        if fecha_nacimiento > date.today():
            raise forms.ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha_nacimiento


class GradoForm(FormularioInstitucional):
    class Meta:
        model = Grado
        fields = ("nivel", "nombre", "seccion", "anio_academico", "tutor", "activo")
        labels = {"anio_academico": "Anio academico"}
        help_texts = {"anio_academico": "Ingrese un anio de cuatro digitos."}
        widgets = {
            "anio_academico": forms.NumberInput(attrs={"min": "1000", "max": "9999"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        tutores = CustomUser.objects.filter(
            institucion=institucion, rol=CustomUser.Rol.PROFESOR, is_active=True
        )
        if self.instance.pk and self.instance.tutor_id:
            tutores = CustomUser.objects.filter(
                Q(
                    institucion=institucion,
                    rol=CustomUser.Rol.PROFESOR,
                    is_active=True,
                )
                | Q(pk=self.instance.tutor_id)
            )
        self.fields["tutor"].queryset = tutores

    def clean_nombre(self):
        return " ".join(self.cleaned_data["nombre"].split())

    def clean_seccion(self):
        return " ".join(self.cleaned_data["seccion"].split())

    def clean_anio_academico(self):
        anio_academico = self.cleaned_data["anio_academico"]
        if anio_academico < 1000 or anio_academico > 9999:
            raise forms.ValidationError(
                "El anio academico debe contener exactamente cuatro digitos."
            )
        return anio_academico

    def clean(self):
        cleaned_data = super().clean()
        campos = ("nivel", "nombre", "seccion", "anio_academico")
        if all(cleaned_data.get(campo) not in (None, "") for campo in campos):
            duplicado = Grado.objects.filter(
                institucion_id=self.instance.institucion_id,
                nivel=cleaned_data["nivel"],
                nombre=cleaned_data["nombre"],
                seccion=cleaned_data["seccion"],
                anio_academico=cleaned_data["anio_academico"],
            ).exclude(pk=self.instance.pk)
            if duplicado.exists():
                raise forms.ValidationError(
                    "Ya existe este grado y seccion para el anio academico indicado."
                )
        return cleaned_data


class CursoForm(FormularioInstitucional):
    class Meta:
        model = Curso
        fields = ("nombre", "codigo", "grado", "profesor", "activo")
        help_texts = {
            "codigo": "El codigo y el nombre no pueden repetirse dentro del grado."
        }
        widgets = {
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        grados = Grado.objects.filter(institucion=institucion, activo=True)
        profesores = CustomUser.objects.filter(
            institucion=institucion, rol=CustomUser.Rol.PROFESOR, is_active=True
        )
        if self.instance.pk:
            grados = Grado.objects.filter(
                Q(institucion=institucion, activo=True) | Q(pk=self.instance.grado_id)
            )
            if self.instance.profesor_id:
                profesores = CustomUser.objects.filter(
                    Q(
                        institucion=institucion,
                        rol=CustomUser.Rol.PROFESOR,
                        is_active=True,
                    )
                    | Q(pk=self.instance.profesor_id)
                )
        self.fields["grado"].queryset = grados
        self.fields["profesor"].queryset = profesores

    def clean_nombre(self):
        return " ".join(self.cleaned_data["nombre"].split())

    def clean_codigo(self):
        return " ".join(self.cleaned_data["codigo"].upper().split())


class MatriculaForm(FormularioInstitucional):
    class Meta:
        model = Matricula
        fields = ("alumno", "grado", "estado")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        self.fields["alumno"].queryset = Alumno.objects.filter(
            institucion=institucion, activo=True
        )
        self.fields["grado"].queryset = Grado.objects.filter(
            institucion=institucion, activo=True
        )
        if self.instance.pk:
            self.fields["alumno"].queryset = Alumno.objects.filter(
                Q(institucion=institucion, activo=True) | Q(pk=self.instance.alumno_id)
            )
            self.fields["grado"].queryset = Grado.objects.filter(
                Q(institucion=institucion, activo=True) | Q(pk=self.instance.grado_id)
            )

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk:
            if (
                cleaned_data.get("alumno")
                and cleaned_data["alumno"].pk != self.instance.alumno_id
            ):
                self.add_error(
                    "alumno",
                    "No se puede cambiar el alumno de una matricula existente.",
                )
            if (
                cleaned_data.get("grado")
                and cleaned_data["grado"].pk != self.instance.grado_id
            ):
                self.add_error(
                    "grado",
                    "No se puede cambiar el grado de una matricula existente.",
                )
        return cleaned_data


class AsistenciaForm(FormularioInstitucional):
    class Meta:
        model = Asistencia
        fields = ("matricula_curso", "fecha", "estado", "observacion")
        labels = {"matricula_curso": "Alumno y curso"}
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["fecha"].initial = date.today().isoformat()
        institucion = getattr(self.usuario_actual, "institucion", None)
        matriculas_curso = MatriculaCurso.objects.filter(
            institucion=institucion, matricula__estado=Matricula.Estado.ACTIVA
        ).select_related("matricula__alumno", "curso")
        if getattr(self.usuario_actual, "rol", None) == CustomUser.Rol.PROFESOR:
            matriculas_curso = matriculas_curso.filter(curso__profesor=self.usuario_actual)
        if self.instance.pk:
            matriculas_curso = MatriculaCurso.objects.filter(
                Q(
                    institucion=institucion,
                    matricula__estado=Matricula.Estado.ACTIVA,
                )
                | Q(pk=self.instance.matricula_curso_id)
            )
            if getattr(self.usuario_actual, "rol", None) == CustomUser.Rol.PROFESOR:
                matriculas_curso = matriculas_curso.filter(
                    curso__profesor=self.usuario_actual
                )
        self.fields["matricula_curso"].queryset = matriculas_curso


class NotaForm(FormularioInstitucional):
    class Meta:
        model = Nota
        fields = ("matricula_curso", "periodo", "evaluacion", "calificacion")
        labels = {"matricula_curso": "Alumno y curso"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        matriculas_curso = MatriculaCurso.objects.filter(
            institucion=institucion,
            matricula__estado=Matricula.Estado.ACTIVA,
            curso__activo=True,
        ).select_related("matricula__alumno", "curso")
        if getattr(self.usuario_actual, "rol", None) == CustomUser.Rol.PROFESOR:
            matriculas_curso = matriculas_curso.filter(curso__profesor=self.usuario_actual)
        if self.instance.pk:
            matriculas_curso = MatriculaCurso.objects.filter(
                Q(
                    institucion=institucion,
                    matricula__estado=Matricula.Estado.ACTIVA,
                    curso__activo=True,
                )
                | Q(pk=self.instance.matricula_curso_id)
            )
            if getattr(self.usuario_actual, "rol", None) == CustomUser.Rol.PROFESOR:
                matriculas_curso = matriculas_curso.filter(
                    curso__profesor=self.usuario_actual
                )
        self.fields["matricula_curso"].queryset = matriculas_curso
