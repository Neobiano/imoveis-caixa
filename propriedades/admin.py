from django.contrib import admin
from .models import Propriedade, ImagemPropriedade

class ImagemPropriedadeInline(admin.TabularInline):
    model = ImagemPropriedade
    extra = 0

@admin.register(Propriedade)
class PropriedadeAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'tipo', 'tipo_imovel', 'cidade', 'estado', 'valor', 'valor_avaliacao', 'desconto', 'area', 'quartos']
    list_filter = ['tipo', 'tipo_imovel', 'cidade', 'estado']
    search_fields = ['codigo', 'endereco', 'descricao']
    inlines = [ImagemPropriedadeInline]
    readonly_fields = ['data_atualizacao']

@admin.register(ImagemPropriedade)
class ImagemPropriedadeAdmin(admin.ModelAdmin):
    list_display = ['propriedade', 'url', 'ordem']
    list_filter = ['propriedade__cidade', 'propriedade__estado']
    search_fields = ['propriedade__codigo', 'url']
