from django.contrib import admin
from django.urls import include, path
from academico.views import inicio


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', inicio, name='inicio'),
    path('academico/', include('academico.urls')),
]
