# academico/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager
import uuid
from django.conf import settings

# 1. Modelo de Usuario para Autenticación (Seguridad)
# Este modelo maneja el login, contraseña segura, permisos, etc.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
   
        rol_ingresado = extra_fields.get('rol')
        if rol_ingresado:
            rol_ingresado = str(rol_ingresado).upper()            
            extra_fields['rol'] = rol_ingresado
        
        roles_validos = [choice[0] for choice in self.model.RolUsuario.choices]
        
        if rol_ingresado not in roles_validos:
            raise ValueError(f"(╥﹏╥) '{rol_ingresado}' no es válido. Usa uno de estos (っ＾▿＾)💨: {roles_validos}")

        return self.create_user(email, password, **extra_fields)
    
class CustomUser(AbstractUser):

    username = None  
    
    class RolUsuario(models.TextChoices):
        DIRECTOR = 'DIRECTOR', 'Director'
        PROFESOR = 'PROFESOR', 'Profesor'
        PADRE = 'PADRE', 'Padre'
        MINEDU = 'MINEDU', 'Trabajador Gobierno'
        COORDINADOR = 'COORDINADOR', 'Personal Académico'

    # Vinculación con el perfil de empleado (opcional si quieres datos extra)
    email = models.EmailField('correo electrónico', unique=True)
    rol = models.CharField(max_length=15, choices=RolUsuario.choices)
    dni = models.CharField(max_length=8, unique=True, null=True, blank=True)
    celular = models.CharField(max_length=9, blank=True, null=True)
    USERNAME_FIELD='email'
    REQUIRED_FIELDS=['rol']
    objects = CustomUserManager()
    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"

class Estudiante(models.Model):
    nombre = models.CharField(max_length=200)
    apellidos = models.CharField(max_length=200)
    dni = models.CharField(max_length=8, unique=True)
    # Vincula al estudiante con su profesor
    profesor_asignado = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellidos}"

class Alerta(models.Model):
    NIVELES = [('BAJO', 'Bajo'), ('MEDIO', 'Medio'), ('ALTO', 'Alto')]
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=10, choices=NIVELES)
    descripcion = models.TextField()
    
    # --- AGREGA ESTAS DOS LÍNEAS QUE FALTABAN ---
    resuelta = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alerta {self.nivel} - {self.estudiante.nombre}"