from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from .models import PerfilUsuario, PreferenciasUsuario, Favorito
from propriedades.models import Propriedade
import json

# Create your views here.

@csrf_exempt
def google_login(request):
    if request.method == 'POST':
        try:
            token = request.POST.get('token')
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            email = idinfo['email']
            google_id = idinfo['sub']
            
            # Busca ou cria o usuário
            user = User.objects.filter(email=email).first()
            if not user:
                username = email.split('@')[0]
                user = User.objects.create_user(username=username, email=email)
            
            # Atualiza ou cria o perfil
            perfil, created = PerfilUsuario.objects.get_or_create(
                usuario=user,
                defaults={'google_id': google_id}
            )
            
            if not created:
                perfil.google_id = google_id
                perfil.save()
            
            login(request, user)
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})

@login_required
def logout_view(request):
    logout(request)
    return JsonResponse({'status': 'success'})

@login_required
def get_preferencias(request):
    perfil = request.user.perfilusuario
    preferencias, created = PreferenciasUsuario.objects.get_or_create(usuario=perfil)
    return JsonResponse({
        'tipo_imovel': preferencias.tipo_imovel,
        'preco_minimo': float(preferencias.preco_minimo) if preferencias.preco_minimo else None,
        'preco_maximo': float(preferencias.preco_maximo) if preferencias.preco_maximo else None,
        'cidade': preferencias.cidade,
        'estado': preferencias.estado,
        'area_minima': float(preferencias.area_minima) if preferencias.area_minima else None,
        'area_maxima': float(preferencias.area_maxima) if preferencias.area_maxima else None,
        'notificacoes_ativas': preferencias.notificacoes_ativas
    })

@login_required
def salvar_preferencias(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            perfil = request.user.perfilusuario
            preferencias, created = PreferenciasUsuario.objects.get_or_create(usuario=perfil)
            
            preferencias.tipo_imovel = data.get('tipo_imovel')
            preferencias.preco_minimo = data.get('preco_minimo')
            preferencias.preco_maximo = data.get('preco_maximo')
            preferencias.cidade = data.get('cidade')
            preferencias.estado = data.get('estado')
            preferencias.area_minima = data.get('area_minima')
            preferencias.area_maxima = data.get('area_maxima')
            preferencias.notificacoes_ativas = data.get('notificacoes_ativas', True)
            
            preferencias.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})

@login_required
def toggle_favorito(request, codigo):
    try:
        propriedade = Propriedade.objects.get(codigo=codigo)
        perfil = request.user.perfilusuario
        
        favorito = Favorito.objects.filter(usuario=perfil, propriedade=propriedade).first()
        
        if favorito:
            favorito.delete()
            return JsonResponse({'status': 'success', 'action': 'removed'})
        else:
            Favorito.objects.create(usuario=perfil, propriedade=propriedade)
            return JsonResponse({'status': 'success', 'action': 'added'})
            
    except Propriedade.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Propriedade não encontrada'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def get_favoritos(request):
    """Retorna a lista de imóveis favoritos do usuário."""
    try:
        favoritos = Favorito.objects.filter(usuario=request.user.perfilusuario).select_related('propriedade')
        print(f"Favoritos encontrados: {favoritos.count()}")
        
        resultado = []
        for f in favoritos:
            try:
                print(f"Processando favorito: {f.propriedade.codigo}")
                print(f"Valor da propriedade: {f.propriedade.valor}")
                item = {
                    'codigo': f.propriedade.codigo,
                    'tipo_imovel': f.propriedade.tipo_imovel,
                    'endereco': f.propriedade.endereco,
                    'estado': f.propriedade.estado,
                    'cidade': f.propriedade.cidade,
                    'bairro': f.propriedade.bairro,
                    'valor': float(f.propriedade.valor) if f.propriedade.valor else None,
                    'desconto': f.propriedade.desconto,
                    'imagem_url': f.propriedade.imagem_url,
                    'data_adicao': f.data_adicao.isoformat(),
                    'link': f.propriedade.link
                }
                resultado.append(item)
            except Exception as e:
                print(f"Erro ao processar favorito {f.propriedade.codigo}: {str(e)}")
                continue
                
        return JsonResponse({'favoritos': resultado})
    except Exception as e:
        print(f"Erro geral em get_favoritos: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
