from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from academico.views import inicio


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', TemplateView.as_view(template_name='public/landing.html'), name='landing'),
    path('dashboard/', inicio, name='inicio'),
    path('academico/', include('academico.urls')),
]
