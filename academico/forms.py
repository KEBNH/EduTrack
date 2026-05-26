from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['dni', 'nombre', 'apellidos', 'celular', 'correo', 'rol', 'activo']
        
        widgets = {
            'dni': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'maxlength': 8, 'placeholder': 'DNI'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'maxlength': 100, 'placeholder': 'Nombre del empleado'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'maxlength': 100, 'placeholder': 'Apellidos del empleado'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 9, 'placeholder': 'Ej. 912345678'}),
            'correo': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100, 'placeholder': 'Correo electrónico'}),           
            'rol': forms.Select(attrs={'class': 'form-select js-select2', 'required': True}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'dni': 'DNI',
            'nombre': 'Nombre',
            'apellidos': 'Apellidos',
            'celular': 'Celular',
            'correo': 'Correo Electrónico',
            'rol': 'Rol',            
            'activo': 'Activo',
        }
    # ==========================
    # VALIDACIONES BACKEND
    # ==========================
    def clean_dni(self):
        dni = self.cleaned_data['dni'].strip()
        if len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener 8 dígitos')
        return dni
    
    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if len(nombre) < 3:
            raise forms.ValidationError('El nombre debe tener al menos 3 caracteres.')
        return nombre

    def clean_apellidos(self):
        apellidos = self.cleaned_data['apellidos'].strip()
        if len(apellidos) < 5:
            raise forms.ValidationError('Los apellidos deben tener al menos 5 caracteres.')
        return apellidos

    def clean_celular(self):
        celular = self.cleaned_data.get('celular')
        if celular:
            if not celular.isdigit():
                raise forms.ValidationError('El celular solo debe contener números.')
            if len(celular) != 9:
                raise forms.ValidationError('El celular debe tener exactamente 9 dígitos.')
        return celular