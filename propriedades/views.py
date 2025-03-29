from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Propriedade
from django.db.models import Q
import requests
import json
from django.conf import settings
import os
import uuid
from datetime import datetime

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

    if codigo := request.GET.get('codigo'):
        queryset = queryset.filter(codigo=codigo)
    
    # Converter queryset para lista de dicionários
    propriedades = list(queryset.values(
        'codigo', 'tipo_imovel', 'endereco', 'bairro', 'cidade', 'estado',
        'valor', 'valor_avaliacao', 'area', 'quartos', 'latitude', 'longitude', 'link',
        'imagem_url', 'desconto', 'matricula_url', 'analise_matricula'
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

@csrf_exempt
@require_http_methods(["POST"])
def analisar_matricula(request):
    """View para analisar a matrícula usando a API do Gemini"""
    try:
        data = json.loads(request.body)
        matricula_url = data.get('matricula_url')
        codigo = data.get('codigo')

        if not matricula_url or not codigo:
            return JsonResponse({'error': 'URL da matrícula ou código do imóvel não fornecidos'}, status=400)
        
        # Buscar a propriedade no banco de dados
        propriedade = Propriedade.objects.get(codigo=codigo)
        
        # Preparar o prompt com a URL da matrícula
        prompt = f"""Analise a matrícula do imóvel disponível em: {matricula_url}
        Identifique os principais pontos de atenção e precauções necessárias para aquisição deste imóvel.
        Inclua informações sobre:
        1. Restrições ou ônus
        2. Área e confrontações
        3. Possíveis problemas ou irregularidades
        4. Recomendações para aquisição
        
        Formate a resposta em markdown com títulos e subtítulos apropriados."""
        
        # Configurar a requisição para a API do Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            "contents": [{
                "parts":[{
                    "text": prompt
                }]
            }]
        }

        # Gerar ID único para esta requisição
        request_id = uuid.uuid4()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Salvar a requisição
        log_dir = os.path.join(settings.BASE_DIR, 'logs', 'gemini_requests')
        os.makedirs(log_dir, exist_ok=True)
        
        request_file = os.path.join(log_dir, f'request_{request_id}_{timestamp}.json')
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump({
                'url': url,
                'headers': headers,
                'data': data,
                'matricula_url': matricula_url,
                'codigo_imovel': codigo
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n=== INÍCIO DA REQUISIÇÃO AO GEMINI ===")
        print(f"ID da requisição: {request_id}")
        print(f"URL da matrícula: {matricula_url}")
        print(f"Payload completo: {json.dumps(data, indent=2)}")
        
        # Fazer a requisição para a API do Gemini
        response = requests.post(url, headers=headers, json=data)
        
        # Salvar a resposta
        response_file = os.path.join(log_dir, f'response_{request_id}_{timestamp}.json')
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump({
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response': response.json() if response.ok else None,
                'error': None if response.ok else response.text
            }, f, ensure_ascii=False, indent=2)
        
        print(f"Status da resposta: {response.status_code}")
        print(f"=== FIM DA REQUISIÇÃO AO GEMINI ===\n")
        
        if response.ok:
            response_json = response.json()
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                analise = response_json['candidates'][0]['content']['parts'][0]['text']
                
                # Salvar a análise no banco de dados
                propriedade.analise_matricula = analise
                propriedade.save()
                
                return JsonResponse({'success': True, 'analise': analise})
            else:
                return JsonResponse({'error': 'Resposta da API não contém o conteúdo esperado'}, status=500)
        else:
            return JsonResponse({'error': f'Erro na API do Gemini: {response.text}'}, status=response.status_code)
            
    except Propriedade.DoesNotExist:
        return JsonResponse({'error': 'Propriedade não encontrada'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido no corpo da requisição'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erro interno do servidor: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def get_propriedade(request, codigo):
    try:
        propriedade = Propriedade.objects.get(codigo=codigo)
        return JsonResponse({
            'codigo': propriedade.codigo,
            'analise_matricula': propriedade.analise_matricula
        })
    except Propriedade.DoesNotExist:
        return JsonResponse({'error': 'Propriedade não encontrada'}, status=404)
