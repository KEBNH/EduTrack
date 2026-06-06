from django import forms

from accounts.models import CustomUser

from .models import Alumno, Apoderado, Asistencia, Curso, Grado, Matricula, Nota


class FormularioInstitucional(forms.ModelForm):
    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_actual = usuario_actual
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class AlumnoForm(FormularioInstitucional):
    class Meta:
        model = Alumno
        fields = ("dni", "nombres", "apellidos", "fecha_nacimiento", "activo")
        widgets = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"})}


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

    def clean(self):
        cleaned_data = super().clean()
        matricula = cleaned_data.get("matricula")
        curso = cleaned_data.get("curso")
        if matricula and curso and matricula.grado_id != curso.grado_id:
            raise forms.ValidationError("El curso no pertenece al grado de la matricula.")
        return cleaned_data
