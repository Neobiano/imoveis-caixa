from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='mapa/', permanent=True), name='index'),
    path('mapa/', views.mapa_view, name='mapa'),
    path('api/propriedades/', views.propriedades_api, name='propriedades_api'),
    path('api/propriedades/<str:codigo>/', views.get_propriedade, name='get_propriedade'),
    path('api/cidades/<str:estado>/', views.cidades_api, name='cidades_api'),
    path('api/bairros/<str:cidade>/', views.bairros_api, name='bairros_api'),
    path('api/analisar-matricula/', views.analisar_matricula, name='analisar_matricula'),
    path('api/proxy-imagem/', views.proxy_imagem, name='proxy_imagem'),
    path('favoritos/', views.favoritos_view, name='favoritos'),
    path('propriedade/<str:codigo>/', views.propriedade_view, name='propriedade'),
] 