from django.contrib import admin
from django.urls import include, path

from academico.views import inicio
from EduTrackApp import views as public_views


urlpatterns = [
    path("", public_views.landing, name="landing"),
    path("nosotros/", public_views.landing_about, name="landing_about"),
    path("contacto/", public_views.landing_contact, name="landing_contact"),
    path("beneficios/", public_views.landing_benefits, name="landing_benefits"),
    path("funcionalidades/", public_views.landing_functionalities, name="landing_functionalities"),
    path("dashboard/", inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("academico/", include("academico.urls")),
]
