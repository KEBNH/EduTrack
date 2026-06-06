from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import CustomUser
from .services import roles_permitidos_para


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo electronico",
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True}),
    )
    password = forms.CharField(
        label="Contrasena",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
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
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()


class CustomUserCreationForm(UsuarioBaseForm):
    class Meta(UsuarioBaseForm.Meta):
        fields = UsuarioBaseForm.Meta.fields + ("rol",)

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        permitidos = roles_permitidos_para(usuario_actual) if usuario_actual else set()
        self.fields["rol"].choices = [
            choice for choice in CustomUser.Rol.choices if choice[0] in permitidos
        ]


class CustomUserUpdateForm(UsuarioBaseForm):
    pass
