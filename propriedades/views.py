from django.shortcuts import render
from django.http import JsonResponse
from .models import Propriedade
from django.db.models import Q

# Create your views here.

def mapa_view(request):
    """View para renderizar a página do mapa"""
    # Obter lista de estados únicos
    estados = Propriedade.objects.values_list('estado', flat=True).distinct().order_by('estado')
    
    # Obter tipos de imóveis únicos
    tipos_imovel = Propriedade.objects.values_list('tipo_imovel', flat=True).distinct().order_by('tipo_imovel')
    
    context = {
        'estados': estados,
        'tipos_imovel': tipos_imovel,
    }
    return render(request, 'propriedades/mapa.html', context)

def propriedades_api(request):
    """API para retornar imóveis filtrados"""
    # Iniciar queryset apenas com imóveis que têm coordenadas
    queryset = Propriedade.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Aplicar filtros
    if estado := request.GET.get('estado'):
        estados = estado.split(',')
        queryset = queryset.filter(estado__in=estados)
        
    if cidade := request.GET.get('cidade'):
        cidades = cidade.split(',')
        queryset = queryset.filter(cidade__in=cidades)
        
    if bairro := request.GET.get('bairro'):
        bairros = bairro.split(',')
        queryset = queryset.filter(bairro__in=bairros)
        
    if tipo_imovel := request.GET.get('tipo_imovel'):
        tipos = tipo_imovel.split(',')
        queryset = queryset.filter(tipo_imovel__in=tipos)
        
    if valor_max := request.GET.get('valor_max'):
        queryset = queryset.filter(valor__lte=valor_max)
        
    if desconto_min := request.GET.get('desconto_min'):
        queryset = queryset.filter(desconto__gte=desconto_min)
        
    if quartos := request.GET.get('quartos'):
        quartos_list = quartos.split(',')
        if quartos_list:
            quartos_q = Q()
            for q in quartos_list:
                quartos_q |= Q(quartos__gte=q)
            queryset = queryset.filter(quartos_q)
    
    # Converter queryset para lista de dicionários
    propriedades = list(queryset.values(
        'codigo', 'tipo_imovel', 'endereco', 'bairro', 'cidade', 'estado',
        'valor', 'valor_avaliacao', 'area', 'quartos', 'latitude', 'longitude', 'link',
        'imagem_url', 'desconto'
    ))
    
    return JsonResponse(propriedades, safe=False)

def cidades_api(request, estado):
    """API para retornar cidades de um estado"""
    cidades = Propriedade.objects.filter(
        estado=estado,
        latitude__isnull=False,
        longitude__isnull=False
    ).values_list('cidade', flat=True).distinct().order_by('cidade')
    
    return JsonResponse(list(cidades), safe=False)

def bairros_api(request, cidade):
    """API para retornar bairros de uma cidade"""
    bairros = Propriedade.objects.filter(
        cidade=cidade,
        latitude__isnull=False,
        longitude__isnull=False
    ).values_list('bairro', flat=True).distinct().order_by('bairro')
    
    return JsonResponse(list(bairros), safe=False)
