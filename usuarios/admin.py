from django.contrib import admin
from .models import PerfilUsuario, PreferenciasUsuario, Favorito

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'google_id', 'data_criacao', 'ultimo_acesso')
    search_fields = ('usuario__username', 'usuario__email', 'google_id')
    list_filter = ('data_criacao', 'ultimo_acesso')

@admin.register(PreferenciasUsuario)
class PreferenciasUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_imovel', 'cidade', 'estado', 'notificacoes_ativas')
    search_fields = ('usuario__usuario__username', 'cidade', 'estado')
    list_filter = ('tipo_imovel', 'estado', 'notificacoes_ativas')

@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'propriedade', 'data_adicao')
    search_fields = ('usuario__usuario__username', 'propriedade__codigo', 'propriedade__endereco')
    list_filter = ('data_adicao',)
