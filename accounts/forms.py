from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm

from .models import CustomUser
from .services import roles_permitidos_para
from .validators import (
    normalizar_email_obligatorio,
    normalizar_texto_obligatorio,
    validar_celular_obligatorio,
    validar_dni_obligatorio,
    validar_rol_obligatorio,
)


class EmailAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Correo o contrasena invalidos.",
        "inactive": "Correo o contrasena invalidos.",
    }
    username = forms.EmailField(
        label="Correo electronico",
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True}),
    )
    password = forms.CharField(
        label="Contrasena",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean_username(self):
        return self.cleaned_data["username"].lower().strip()

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages["inactive"],
                code="inactive",
            )


class UsuarioBaseForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("dni", "first_name", "last_name", "celular", "email")
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellidos",
            "email": "Correo electronico",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("dni", "first_name", "last_name", "celular", "email"):
            self.fields[field_name].required = True
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_dni(self):
        return validar_dni_obligatorio(self.cleaned_data["dni"])

    def clean_first_name(self):
        return normalizar_texto_obligatorio(
            self.cleaned_data["first_name"],
            "El nombre",
        )

    def clean_last_name(self):
        return normalizar_texto_obligatorio(
            self.cleaned_data["last_name"],
            "Los apellidos",
        )

    def clean_celular(self):
        return validar_celular_obligatorio(self.cleaned_data["celular"])

    def clean_email(self):
        return normalizar_email_obligatorio(self.cleaned_data["email"])


class CustomUserCreationForm(UsuarioBaseForm):
    class Meta(UsuarioBaseForm.Meta):
        fields = UsuarioBaseForm.Meta.fields + ("rol",)

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.roles_permitidos = (
            roles_permitidos_para(usuario_actual) if usuario_actual else set()
        )
        self.fields["rol"].choices = [
            choice
            for choice in CustomUser.Rol.choices
            if choice[0] in self.roles_permitidos
        ]
        self.fields["rol"].required = True

    def clean_rol(self):
        return validar_rol_obligatorio(
            self.cleaned_data["rol"],
            self.roles_permitidos,
        )


class CustomUserUpdateForm(UsuarioBaseForm):
    pass


class ActivarCuentaForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
