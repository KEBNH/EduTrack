from django.contrib import admin
from django.urls import path
from .views import  inicio, portada, iniciar_sesion, cerrar_sesion,crear_usuario, listar_elementos

urlpatterns = [
    path('', portada, name='portada'),
    path('login/', iniciar_sesion, name='login'),
    path('logout/', cerrar_sesion, name='logout'), 
    path('panel/', inicio, name='inicio'),
    path('panel/registro',crear_usuario,name="crear_usuarios"),
    path('panel/lista/<str:tipo>/', listar_elementos, name='listar_elementos'),
]