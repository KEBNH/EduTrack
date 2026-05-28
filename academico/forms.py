# academico/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import CustomUser
User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Formulario unificado para registro de usuarios"""
    
    # Agregamos los campos que movimos de Employee a CustomUser
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    dni = forms.CharField(max_length=8, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DNI'}))
    celular = forms.CharField(max_length=9, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Celular'}))
    rol = forms.ChoiceField(choices=CustomUser.RolUsuario.choices, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "rol", "dni", "celular")

    def __init__(self, *args, **kwargs):
        # Sacamos los roles permitidos que nos envíe la vista
        self.roles_permitidos = kwargs.pop('roles_permitidos', None)
        super().__init__(*args, **kwargs)
        
        # Si la vista nos mandó roles, filtramos el desplegable
        if self.roles_permitidos:
            opciones_filtradas = [(rol, rol) for rol in self.roles_permitidos]
            self.fields['rol'].choices = opciones_filtradas

    # Validaciones para mantener la integridad de los datos
    def clean_dni(self):
        dni = self.cleaned_data.get('dni', '').strip()
        if len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener 8 dígitos.')
        return dni