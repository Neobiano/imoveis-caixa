from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # URLs do django-allauth
    path('', include('propriedades.urls')),  # URLs do app propriedades na raiz
    path('api/', include('propriedades.urls')),
    path('api/usuarios/', include('usuarios.urls')),  # URLs do app usuarios
]

# Adicionar URLs para arquivos estáticos em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 