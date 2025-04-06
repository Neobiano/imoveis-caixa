from django.urls import path
from . import views

urlpatterns = [
    path('preferencias/', views.get_preferencias, name='get_preferencias'),
    path('preferencias/salvar/', views.salvar_preferencias, name='salvar_preferencias'),
    path('favoritos/', views.get_favoritos, name='get_favoritos'),
    path('favoritos/<str:codigo>/', views.toggle_favorito, name='toggle_favorito'),
] 