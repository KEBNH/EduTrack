from datetime import date

from django import forms

from accounts.models import CustomUser

from .models import Alumno, Apoderado, Asistencia, Curso, Grado, Matricula, Nota


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


class GradoForm(FormularioInstitucional):
    class Meta:
        model = Grado
        fields = ("nivel", "nombre", "seccion", "anio_academico", "activo")


class CursoForm(FormularioInstitucional):
    class Meta:
        model = Curso
        fields = ("nombre", "codigo", "grado", "profesor", "activo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        self.fields["grado"].queryset = Grado.objects.filter(institucion=institucion)
        self.fields["profesor"].queryset = CustomUser.objects.filter(
            institucion=institucion, rol=CustomUser.Rol.PROFESOR, is_active=True
        )


class MatriculaForm(FormularioInstitucional):
    class Meta:
        model = Matricula
        fields = ("alumno", "grado", "anio_academico", "estado")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        self.fields["alumno"].queryset = Alumno.objects.filter(
            institucion=institucion, activo=True
        )
        self.fields["grado"].queryset = Grado.objects.filter(
            institucion=institucion, activo=True
        )


class AsistenciaForm(FormularioInstitucional):
    class Meta:
        model = Asistencia
        fields = ("matricula", "fecha", "estado", "observacion")
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        matriculas = Matricula.objects.filter(institucion=institucion, estado="ACTIVA")
        if getattr(self.usuario_actual, "rol", None) == CustomUser.Rol.PROFESOR:
            matriculas = matriculas.filter(grado__cursos__profesor=self.usuario_actual).distinct()
        self.fields["matricula"].queryset = matriculas


class NotaForm(FormularioInstitucional):
    class Meta:
        model = Nota
        fields = ("matricula", "curso", "periodo", "evaluacion", "calificacion")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        institucion = getattr(self.usuario_actual, "institucion", None)
        matriculas = Matricula.objects.filter(institucion=institucion, estado="ACTIVA")
        cursos = Curso.objects.filter(institucion=institucion, activo=True)
        if getattr(self.usuario_actual, "rol", None) == CustomUser.Rol.PROFESOR:
            cursos = cursos.filter(profesor=self.usuario_actual)
            matriculas = matriculas.filter(grado__cursos__in=cursos).distinct()
        self.fields["matricula"].queryset = matriculas
        self.fields["curso"].queryset = cursos
