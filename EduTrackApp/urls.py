from django.contrib import admin
from django.urls import include, path, re_path
from . import views

from academico.views import inicio
from EduTrackApp import views as public_views
from .views import landing_faq


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.landing_home, name='landing'),
    path('nosotros/', views.landing_about, name='landing_about'),
    path('contacto/', views.landing_contact, name='landing_contact'),
    path('beneficios/', views.landing_benefits, name='landing_benefits'),
    path('funcionalidades/', views.landing_functionalities, name='landing_functionalities'),
    path('products.html', views.landing_faq, name='landing_faq'),

    re_path(
        r'^(?:beneficios|nosotros|contacto|funcionalidades)/(?P<page>index|about|contact|products|courses|instructors|beneficios|funcionalidades)\.html$',
        views.legacy_landing_redirect,
        name='legacy_landing_redirect_nested'
    ),

    re_path(
        r'^(?P<page>index|about|contact|courses|instructors|beneficios|funcionalidades)\.html$',
        views.legacy_landing_redirect,
        name='legacy_landing_redirect'
    ),

    path('dashboard/', views.dashboard, name='inicio'),
    path('accounts/', include('accounts.urls')),
    path('academico/', include('academico.urls')),
]