from django.urls import path

from . import views


urlpatterns = [
    path('', views.portada, name='portada'),
    path('academico/', views.inicio, name='inicio'),
    path('academico/estudiante/', views.estudiante, name='estudiante'),
]
