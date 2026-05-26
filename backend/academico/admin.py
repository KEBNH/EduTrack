from django.contrib import admin

from .models import AlertaRiesgo, Asistencia, Calificacion, Curso, Estudiante, Institucion


admin.site.register(Institucion)
admin.site.register(Estudiante)
admin.site.register(Curso)
admin.site.register(Asistencia)
admin.site.register(Calificacion)
admin.site.register(AlertaRiesgo)
