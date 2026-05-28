from django.views.decorators.cache import never_cache
from django.shortcuts import render, get_object_or_404,redirect
from django.views.generic import (ListView, CreateView, UpdateView, DeleteView, DetailView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required 
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib import messages
#from accounts.mixins import RolRequiredMixin
from .models import CustomUser, Estudiante, Alerta
from .forms import CustomUserCreationForm


# ===============================================
# ====== VISTAS PÚBLICAS Y DE ACCESO (TU TRABAJO)
# ===============================================

def portada(request):
    return render(request, 'portada.html')


# Vista de login
def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect('inicio')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            auth_login(request, user)
            return redirect('inicio')
        else:
            error = "El usuario o la contraseña son incorrectos. Intenta nuevamente."
            return render(request, 'login.html', {'error': error})
    
    return render(request, 'login.html')

# Vista de logout
@login_required
def cerrar_sesion(request):
    auth_logout(request)
    return redirect('login')

# Vista principal del dashboard
@never_cache
@login_required
def inicio(request):
    # Contexto según el rol del usuario
    context = {}
    if request.user.rol == 'DIRECTOR':
        # Directores ven estadísticas generales
        context['total_estudiantes'] = Estudiante.objects.count()
        context['total_profesores'] = CustomUser.objects.filter(rol='PROFESOR').count()
        context['alertas_altas'] = Alerta.objects.filter(nivel='ALTO', resuelta=False).count()
        
    elif request.user.rol == 'PROFESOR':
        # Profesores ven sus estudiantes
        context['estudiantes'] = Estudiante.objects.filter(profesor_asignado=request.user)
        context['alertas_pendientes'] = Alerta.objects.filter(
            estudiante__profesor_asignado=request.user, 
            resuelta=False
        )
        
    elif request.user.rol == 'PADRE':
        # Padres ven a sus hijos
        context['hijos'] = request.user.hijos.all()
        context['alertas_hijos'] = Alerta.objects.filter(
            estudiante__padres=request.user, 
            resuelta=False
        )
        
    elif request.user.rol == 'MINEDU':
        # Empleados MINEDU ven estadísticas a nivel nacional
        context['total_directores'] = CustomUser.objects.filter(rol='DIRECTOR').count()
        context['total_profesores'] = CustomUser.objects.filter(rol='PROFESOR').count()
        context['total_estudiantes'] = Estudiante.objects.count()
    
    return render(request, 'bashboard.html', context)
@never_cache
@login_required
def crear_usuario(request):
    # 1. ¿Quién está logueado y qué puede crear?
    if request.user.rol == 'DIRECTOR':
        roles_permitidos = ['PROFESOR']
        titulo_formulario = "Crear Nuevo Profesor"
    elif request.user.rol == 'PROFESOR':
        roles_permitidos = ['PADRE']
        titulo_formulario = "Crear Cuenta de Padre"
    else:
        messages.error(request, "No tienes permisos para crear usuarios.")
        return redirect('inicio')

    # 2. Procesar el formulario
    if request.method == 'POST':
        # Le pasamos la regla al formulario
        user_form = CustomUserCreationForm(request.POST, roles_permitidos=roles_permitidos)

        if user_form.is_valid():
            # Guardamos el usuario y su contraseña encriptada (Django lo hace solo)
            nuevo_user = user_form.save() 
            messages.success(request, f"¡Éxito! Usuario '{nuevo_user.username}' creado correctamente.")
            return redirect('inicio')
    else:
        # Formulario vacío para mostrar por primera vez
        user_form = CustomUserCreationForm(roles_permitidos=roles_permitidos)

    context = {
        'user_form': user_form,
        'titulo': titulo_formulario
    }
    return render(request, 'crear_usuario.html', context)
@login_required
@never_cache
def listar_elementos(request, tipo):
    context = {}
    
    # 1. Si la URL dice 'profesores'
    if tipo == 'profesores':
        context['titulo'] = "Directorio de Profesores"
        context['datos'] = CustomUser.objects.filter(rol='PROFESOR')
        context['tipo_lista'] = 'profesores' # Esta bandera le dirá al HTML qué columnas dibujar
        
    # 2. Si la URL dice 'estudiantes'
    elif tipo == 'estudiantes':
        context['titulo'] = "Padrón General de Estudiantes"
        context['datos'] = Estudiante.objects.all()
        context['tipo_lista'] = 'estudiantes'
        
    else:
        # Si alguien escribe una tontería en la URL, lo pateas al inicio
        return redirect('inicio')
        
    return render(request, 'listado_general.html', context)