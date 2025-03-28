from django.urls import path
from . import views

urlpatterns = [
    path('mapa/', views.mapa_view, name='mapa'),
    path('api/propriedades/', views.propriedades_api, name='propriedades_api'),
    path('api/cidades/<str:estado>/', views.cidades_api, name='cidades_api'),
    path('api/bairros/<str:cidade>/', views.bairros_api, name='bairros_api'),
] 