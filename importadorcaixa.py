import os
import sys
import django
import requests
import csv
from io import StringIO
from decimal import Decimal
import logging
from datetime import datetime
import codecs
from geopy.geocoders import Nominatim, Here
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
from validacao_geografica import ValidadorGeografico
import urllib3
import random

# Desabilitar avisos de certificado não verificado
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade, ImagemPropriedade

# Configuração de logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'importacao.log')

# Criar um handler personalizado para garantir flush imediato
class ImmediateFlushHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()
        os.fsync(self.stream.fileno())  # Força a escrita no disco

# Configurar o logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remover handlers existentes
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Adicionar handlers
file_handler = ImmediateFlushHandler(log_file, encoding='utf-8', mode='a')
console_handler = logging.StreamHandler()

# Configurar formato
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Adicionar handlers ao logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Log inicial para testar
logger.info("Iniciando configuração de logging")

# Carregar variáveis de ambiente
load_dotenv()

class ImportadorCaixa:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{}.csv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        # Carregar chaves da API do arquivo .env
        self.api_keys = [
            os.environ.get('HERE_API_KEY_1'),
            os.environ.get('HERE_API_KEY_2'),
            os.environ.get('HERE_API_KEY_3')
        ]
        self.current_api_key_index = 0
        self.validador_geografico = ValidadorGeografico()
        self.todas_apis_indisponiveis = False  # Nova flag para controlar disponibilidade das APIs
        self.apis_com_erro = set()  # Conjunto para rastrear quais APIs já retornaram erro
        logger.info("Iniciando nova sessão de importação")

        # Inicializar a sessão com uma visita à página principal
        try:
            logger.info("Inicializando sessão com visita à página principal...")
            response = self.session.get('https://venda-imoveis.caixa.gov.br/', headers=self.headers, verify=False)
            response.raise_for_status()
            time.sleep(2)  # Aguarda 2 segundos antes de prosseguir
        except Exception as e:
            logger.error(f"Erro ao inicializar sessão: {str(e)}")

    def _get_next_api_key(self):
        """Retorna a próxima API key disponível."""
        self.current_api_key_index = (self.current_api_key_index + 1) % len(self.api_keys)
        return self.api_keys[self.current_api_key_index]

    def _limpar_valor(self, valor_texto):
        """Converte texto de valor monetário para Decimal"""
        if not valor_texto:
            return Decimal('0')
        valor = valor_texto.replace('R$', '').replace('.', '').replace(',', '.').strip()
        return Decimal(valor)

    def _extrair_area_quartos(self, descricao):
        """Extrai área e número de quartos da descrição"""
        area_total = None
        area_privativa = None
        area_terreno = None
        quartos = None
        
        if 'área total' in descricao.lower():
            import re
            match = re.search(r'(\d+[\.,]\d+)\s*de\s*área\s*total', descricao)
            if match:
                area_total = Decimal(match.group(1).replace(',', '.'))
        
        if 'área privativa' in descricao.lower():
            match = re.search(r'(\d+[\.,]\d+)\s*de\s*área\s*privativa', descricao)
            if match:
                area_privativa = Decimal(match.group(1).replace(',', '.'))
        
        if 'área do terreno' in descricao.lower():
            match = re.search(r'(\d+[\.,]\d+)\s*de\s*área\s*do\s*terreno', descricao)
            if match:
                area_terreno = Decimal(match.group(1).replace(',', '.'))

        if 'qto(s)' in descricao:
            match = re.search(r'(\d+)\s*qto\(s\)', descricao)
            if match:
                quartos = int(match.group(1))

        return area_total, area_privativa, area_terreno, quartos

    def _baixar_csv(self, url):
        """Baixa um arquivo CSV da URL fornecida, tentando HTTPS primeiro e HTTP como fallback."""
        def tentar_decodificar(content):
            """Tenta decodificar o conteúdo com diferentes codificações"""
            encodings = ['latin1', 'iso-8859-1', 'cp1252', 'utf-8', 'utf-16', 'ascii']
            for encoding in encodings:
                try:
                    texto = content.decode(encoding)
                    # Verifica se o texto decodificado contém partes do cabeçalho esperado
                    if ('imovel' in texto.lower() or 'imóvel' in texto.lower()) and \
                       ('UF' in texto or 'Cidade' in texto or 'Bairro' in texto):
                        logger.info(f"Conteúdo decodificado com sucesso usando {encoding}")
                        return texto
                except UnicodeDecodeError as e:
                    logger.warning(f"Falha ao decodificar com {encoding}: {str(e)}")
                    continue
            logger.error("Não foi possível decodificar o conteúdo com nenhuma codificação")
            # Log dos primeiros bytes do conteúdo para debug
            logger.error(f"Primeiros 100 bytes do conteúdo: {content[:100]}")
            # Log do conteúdo em hexadecimal para debug
            logger.error("Conteúdo em hexadecimal:")
            logger.error(' '.join(f'{b:02x}' for b in content[:100]))
            return None

        try:
            # Primeiro tenta com HTTPS, ignorando verificação de certificado
            logger.info(f"Tentando baixar CSV via HTTPS: {url}")
            
            # Adiciona um delay aleatório entre 1 e 3 segundos
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, headers=self.headers, timeout=30, verify=False)
            response.raise_for_status()
            
            # Log do tipo de conteúdo e tamanho
            logger.info(f"Tipo de conteúdo: {response.headers.get('content-type', 'não especificado')}")
            logger.info(f"Tamanho do conteúdo: {len(response.content)} bytes")
            logger.info(f"Headers da resposta:")
            for header, value in response.headers.items():
                logger.info(f"  {header}: {value}")
            
            # Tenta decodificar o conteúdo
            content = response.content
            texto_decodificado = tentar_decodificar(content)
            
            if texto_decodificado:
                # Log dos primeiros 500 caracteres do conteúdo
                logger.info(f"Primeiros 500 caracteres do conteúdo baixado:")
                logger.info(texto_decodificado[:500])
                return texto_decodificado
                
            logger.warning("Não foi possível decodificar o conteúdo com nenhuma codificação")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Falha ao baixar CSV via HTTPS: {str(e)}")
            logger.error(f"Detalhes do erro: {type(e).__name__}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Headers da resposta de erro:")
                for header, value in e.response.headers.items():
                    logger.error(f"  {header}: {value}")
                logger.error(f"Conteúdo da resposta de erro:")
                logger.error(e.response.text[:500])
            
            # Se falhou, tenta com HTTP
            http_url = url.replace('https://', 'http://')
            try:
                logger.info(f"Tentando baixar via HTTP: {http_url}")
                
                # Adiciona um delay aleatório entre 1 e 3 segundos
                time.sleep(random.uniform(1, 3))
                
                response = self.session.get(http_url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # Log do tipo de conteúdo e tamanho
                logger.info(f"Tipo de conteúdo: {response.headers.get('content-type', 'não especificado')}")
                logger.info(f"Tamanho do conteúdo: {len(response.content)} bytes")
                logger.info(f"Headers da resposta:")
                for header, value in response.headers.items():
                    logger.info(f"  {header}: {value}")
                
                # Tenta decodificar o conteúdo
                content = response.content
                texto_decodificado = tentar_decodificar(content)
                
                if texto_decodificado:
                    # Log dos primeiros 500 caracteres do conteúdo
                    logger.info(f"Primeiros 500 caracteres do conteúdo baixado:")
                    logger.info(texto_decodificado[:500])
                    return texto_decodificado
                    
                logger.warning("Não foi possível decodificar o conteúdo com nenhuma codificação")
                return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Falha ao baixar CSV via HTTP: {str(e)}")
                logger.error(f"Detalhes do erro: {type(e).__name__}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Status code: {e.response.status_code}")
                    logger.error(f"Headers da resposta de erro:")
                    for header, value in e.response.headers.items():
                        logger.error(f"  {header}: {value}")
                    logger.error(f"Conteúdo da resposta de erro:")
                    logger.error(e.response.text[:500])
                raise

    def _processar_csv(self, conteudo_csv):
        """Processa o conteúdo do CSV"""
        try:
            # Remover linhas vazias e espaços extras
            linhas = [linha for linha in conteudo_csv.splitlines() if linha.strip()]
            logger.info(f"Total de linhas no CSV após remoção de vazias: {len(linhas)}")
            
            # Encontrar a linha do cabeçalho
            linha_cabecalho = None
            for i, linha in enumerate(linhas):
                if 'N° do imóvel' in linha:
                    linha_cabecalho = i
                    logger.info(f"Cabeçalho encontrado na linha {i}")
                    break
            
            if linha_cabecalho is None:
                logger.error("Cabeçalho não encontrado no CSV!")
                logger.error("Primeiras 5 linhas do arquivo:")
                for i, linha in enumerate(linhas[:5]):
                    logger.error(f"Linha {i}: {linha}")
                return []
            
            # Criar um novo CSV apenas com o cabeçalho e os dados
            csv_processado = StringIO()
            csv_processado.write(linhas[linha_cabecalho] + '\n')  # Cabeçalho
            
            # Adicionar apenas as linhas que têm dados
            linhas_validas = 0
            for linha in linhas[linha_cabecalho + 1:]:
                if linha.strip() and ';' in linha:
                    csv_processado.write(linha + '\n')
                    linhas_validas += 1
            
            logger.info(f"Total de linhas válidas encontradas: {linhas_validas}")
            
            csv_processado.seek(0)
            
            # Usar DictReader para processar o CSV
            leitor = csv.DictReader(csv_processado, delimiter=';')
            
            # Processar as linhas
            dados = []
            for i, linha in enumerate(leitor, 1):
                try:
                    # Limpar espaços em branco dos valores
                    item = {k.strip(): v.strip() for k, v in linha.items() if k and k.strip()}
                    if item:
                        logger.debug(f"Linha {i} processada com sucesso")
                        dados.append(item)
                    else:
                        logger.warning(f"Linha {i} está vazia após processamento")
                except Exception as e:
                    logger.error(f"Erro ao processar linha {i}: {str(e)}")
                    logger.error(f"Conteúdo da linha: {linha}")
                    continue
            
            logger.info(f"Total de imóveis processados com sucesso: {len(dados)}")
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao processar CSV: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            logger.error("Stack trace completo:")
            logger.error(traceback.format_exc())
            return []

    def _normalizar_texto(self, texto):
        """Normaliza o texto removendo espaços extras e caracteres problemáticos"""
        if not texto:
            return ""
            
        # Mapeamento de caracteres especiais comuns
        mapa_caracteres = {
            'Nº': 'N',
            'Nø': 'N',
            'Preço': 'Preco',
            'Endereço': 'Endereco',
            'Descrição': 'Descricao',
            'Município': 'Municipio',
            'imóvel': 'imovel',
            'avaliação': 'avaliacao'
        }
        
        texto = texto.strip()
        
        # Aplicar substituições
        for original, substituicao in mapa_caracteres.items():
            texto = texto.replace(original, substituicao)
            
        return texto

    def _limpar_banco(self):
        """Limpa todos os registros do banco antes da importação"""
        try:
            total_deletado = Propriedade.objects.all().delete()
            logger.info(f"Banco de dados limpo. {total_deletado[0]} registros removidos.")
        except Exception as e:
            logger.error(f"Erro ao limpar banco de dados: {str(e)}")

    def _extrair_tipo_imovel(self, descricao):
        """Extrai o tipo do imóvel da descrição (texto antes da primeira vírgula)"""
        if not descricao:
            return None
        
        partes = descricao.split(',', 1)
        if not partes:
            return None
            
        tipo = partes[0].strip()
        return tipo if tipo else None

    def _obter_coordenadas(self, endereco, cidade, estado):
        """Obtém as coordenadas de um endereço usando a API do Here Maps"""
        if self.todas_apis_indisponiveis:
            logger.warning("Todas as APIs do Here Maps estão indisponíveis. Pulando consulta de coordenadas.")
            return None, None

        try:
            # Tentar obter coordenadas com a API atual
            api_key = self.api_keys[self.current_api_key_index]
            if not api_key:
                logger.error(f"API key {self.current_api_key_index + 1} não configurada")
                return None, None

            url = f"https://geocode.search.hereapi.com/v1/geocode"
            params = {
                'q': endereco,
                'apiKey': api_key
            }

            response = requests.get(url, params=params)
            
            # Se receber erro 429 (Too Many Requests) ou 401 (Unauthorized)
            if response.status_code in [429, 401]:
                logger.error(f"API {self.current_api_key_index + 1} retornou erro {response.status_code}")
                self.apis_com_erro.add(self.current_api_key_index)
                
                # Se todas as APIs já retornaram erro
                if len(self.apis_com_erro) == len(self.api_keys):
                    logger.error("Todas as APIs do Here Maps retornaram erro. Desabilitando consultas.")
                    self.todas_apis_indisponiveis = True
                    return None, None
                
                # Tentar próxima API
                self.current_api_key_index = (self.current_api_key_index + 1) % len(self.api_keys)
                return self._obter_coordenadas(endereco, cidade, estado)

            response.raise_for_status()
            data = response.json()

            if data.get('items'):
                position = data['items'][0].get('position', {})
                latitude = position.get('lat')
                longitude = position.get('lng')

                if latitude and longitude:
                    # Validar as coordenadas
                    if self.validador_geografico.validar_coordenadas(latitude, longitude, cidade, estado):
                        return latitude, longitude
                    else:
                        logger.warning(f"Coordenadas inválidas para o endereço: {endereco}")
                        return None, None

            logger.warning(f"Nenhuma coordenada encontrada para o endereço: {endereco}")
            return None, None

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter coordenadas: {str(e)}")
            return None, None

    def _obter_url_imagem(self, codigo):
        """Obtém a URL da imagem do imóvel usando o padrão F{id_imovel}21 com padding de zeros"""
        try:
            # Garantir que o código tenha 13 dígitos (preenchendo com zeros à esquerda)
            codigo_padded = str(codigo).zfill(13)
            url = f"https://venda-imoveis.caixa.gov.br/fotos/F{codigo_padded}21.jpg"
            logger.info(f"URL da imagem gerada: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Erro ao gerar URL da imagem: {str(e)}")
            return None

    def _processar_imovel(self, dados):
        """Processa os dados de um imóvel do CSV"""
        try:
            codigo = dados.get('N° do imóvel', '').strip()
            logger.info(f"\nProcessando imóvel {codigo}")
            
            if not codigo:
                logger.error("Imóvel sem código, ignorando")
                return None

            # Verificar se o imóvel já existe e tem coordenadas
            imovel_existente = Propriedade.objects.filter(codigo=codigo).first()
            if imovel_existente and imovel_existente.latitude is not None and imovel_existente.longitude is not None:
                logger.info(f"Imóvel {codigo} já possui coordenadas cadastradas. Pulando validação.")
                return None

            # Extrair área e quartos da descrição
            descricao = dados.get('Descrição', '').strip()
            logger.info(f"Descrição do imóvel: {descricao[:100]}...")
            
            area_total, area_privativa, area_terreno, quartos = self._extrair_area_quartos(descricao)
            logger.info(f"Áreas extraídas - Total: {area_total}, Privativa: {area_privativa}, Terreno: {area_terreno}, Quartos: {quartos}")

            # Extrair tipo do imóvel
            tipo_imovel = self._extrair_tipo_imovel(descricao)
            logger.info(f"Tipo do imóvel: {tipo_imovel}")

            # Processar valores monetários
            valor = self._limpar_valor(dados.get('Preço', '0'))
            valor_avaliacao = self._limpar_valor(dados.get('Valor de avaliação', '0'))
            logger.info(f"Valores processados - Preço: R$ {valor}, Avaliação: R$ {valor_avaliacao}")
            
            # Processar desconto
            desconto_texto = dados.get('Desconto', '0').replace('%', '').strip()
            try:
                desconto = Decimal(desconto_texto)
                logger.info(f"Desconto processado: {desconto}%")
            except Exception as e:
                logger.error(f"Erro ao processar desconto '{desconto_texto}': {str(e)}")
                desconto = Decimal('0')

            endereco = dados.get('Endereço', '').strip()
            bairro = dados.get('Bairro', '').strip()
            cidade = dados.get('Cidade', '').strip()
            estado = dados.get('UF', '').strip()
            link = dados.get('Link de acesso', '').strip()
            
            logger.info(f"Endereço completo: {endereco}, {bairro}, {cidade} - {estado}")

            # Gerar URL da matrícula
            matricula_url = None
            if codigo:
                # Formatar o código com zeros à esquerda se necessário
                codigo_formatado = codigo.zfill(13)
                if estado:
                    matricula_url = f"https://venda-imoveis.caixa.gov.br/editais/matricula/{estado}/{codigo_formatado}.pdf"
                    logger.info(f"URL da matrícula gerada: {matricula_url}")

            # Montar o objeto do imóvel
            imovel = {
                'codigo': codigo,
                'tipo': 'Residencial',  # Valor padrão
                'tipo_imovel': tipo_imovel,
                'endereco': endereco,
                'bairro': bairro,
                'cidade': cidade,
                'estado': estado,
                'valor': valor,
                'valor_avaliacao': valor_avaliacao,
                'desconto': desconto,
                'descricao': descricao,
                'modalidade_venda': dados.get('Modalidade de venda', '').strip(),
                'area': area_privativa or area_total or area_terreno or Decimal('0'),
                'area_total': area_total,
                'area_privativa': area_privativa,
                'area_terreno': area_terreno,
                'quartos': quartos or 0,
                'link': link,
                'matricula_url': matricula_url
            }

            # Coletar coordenadas apenas para imóveis novos ou sem coordenadas
            endereco_completo = f"{endereco}, {cidade}, {estado}, Brasil"
            logger.info(f"Buscando coordenadas para: {endereco_completo}")
            
            latitude, longitude = self._obter_coordenadas(endereco_completo, cidade, estado)
            imovel['latitude'] = latitude
            imovel['longitude'] = longitude
            
            if latitude and longitude:
                logger.info(f"Coordenadas obtidas: Latitude={latitude}, Longitude={longitude}")
            else:
                logger.warning(f"Não foi possível obter coordenadas para o imóvel {codigo}")

            # Obter URL da imagem usando apenas o código
            logger.info(f"Buscando imagem para o imóvel {codigo}")
            imovel['imagem_url'] = self._obter_url_imagem(codigo)
            if imovel['imagem_url']:
                logger.info(f"URL da imagem encontrada: {imovel['imagem_url']}")
            else:
                logger.warning(f"Nenhuma imagem encontrada para o imóvel {codigo}")

            logger.info(f"Imóvel {codigo} processado com sucesso")
            return imovel
            
        except Exception as e:
            logger.error(f"Erro ao processar dados do imóvel {dados.get('N° do imóvel', 'sem código')}: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            logger.error("Stack trace completo:")
            logger.error(traceback.format_exc())
            return None

    def _salvar_imovel(self, dados_imovel):
        """Salva ou atualiza um imóvel no banco de dados"""
        try:
            if not dados_imovel or not dados_imovel.get('codigo'):
                logger.warning("Tentativa de salvar imóvel sem código")
                return None

            # Garantir que os campos numéricos sejam do tipo correto
            dados_para_salvar = {
                'codigo': dados_imovel['codigo'],
                'tipo': dados_imovel.get('tipo', 'Residencial'),
                'tipo_imovel': dados_imovel.get('tipo_imovel'),
                'endereco': dados_imovel.get('endereco', ''),
                'bairro': dados_imovel.get('bairro', ''),
                'cidade': dados_imovel.get('cidade', ''),
                'estado': dados_imovel.get('estado', ''),
                'valor': Decimal(str(dados_imovel.get('valor', '0'))),
                'valor_avaliacao': Decimal(str(dados_imovel.get('valor_avaliacao', '0'))),
                'desconto': Decimal(str(dados_imovel.get('desconto', '0'))),
                'descricao': dados_imovel.get('descricao', ''),
                'modalidade_venda': dados_imovel.get('modalidade_venda', ''),
                'area': Decimal(str(dados_imovel.get('area', '0'))),
                'area_total': Decimal(str(dados_imovel.get('area_total', '0'))) if dados_imovel.get('area_total') else None,
                'area_privativa': Decimal(str(dados_imovel.get('area_privativa', '0'))) if dados_imovel.get('area_privativa') else None,
                'area_terreno': Decimal(str(dados_imovel.get('area_terreno', '0'))) if dados_imovel.get('area_terreno') else None,
                'quartos': int(dados_imovel.get('quartos', 0)),
                'link': dados_imovel.get('link', ''),
                'latitude': Decimal(str(dados_imovel.get('latitude', '0'))) if dados_imovel.get('latitude') else None,
                'longitude': Decimal(str(dados_imovel.get('longitude', '0'))) if dados_imovel.get('longitude') else None,
                'imagem_url': dados_imovel.get('imagem_url'),
                'matricula_url': dados_imovel.get('matricula_url'),
            }

            logger.debug(f"Tentando salvar imóvel com dados: {dados_para_salvar}")

            imovel, criado = Propriedade.objects.update_or_create(
                codigo=dados_para_salvar['codigo'],
                defaults=dados_para_salvar
            )

            status = 'criado' if criado else 'atualizado'
            logger.info(f"Imóvel {dados_para_salvar['codigo']} {status} com sucesso")
            return imovel

        except Exception as e:
            logger.error(f"Erro ao salvar imóvel {dados_imovel.get('codigo', 'sem código')}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _validar_csv(self, conteudo):
        """Valida se o conteúdo parece ser um CSV válido"""
        try:
            # Verificar se tem o cabeçalho esperado
            colunas_esperadas = [
                'N° do imóvel',
                'UF',
                'Cidade',
                'Bairro',
                'Endereço',
                'Preço',
                'Valor de avaliação',
                'Desconto',
                'Descrição',
                'Modalidade de venda',
                'Link de acesso'
            ]
            
            # Remover linhas vazias e espaços extras
            linhas = [linha.strip() for linha in conteudo.splitlines() if linha.strip()]
            
            # Procurar linha do cabeçalho
            for linha in linhas:
                if 'N° do imóvel' in linha or 'Nº do imóvel' in linha:
                    # Verificar se a maioria das colunas esperadas está presente
                    colunas_encontradas = 0
                    for coluna in colunas_esperadas:
                        if coluna in linha:
                            colunas_encontradas += 1
                    
                    # Se encontrou pelo menos 70% das colunas esperadas
                    if colunas_encontradas >= len(colunas_esperadas) * 0.7:
                        print("Cabeçalho válido encontrado")
                        return True
            
            print("Cabeçalho válido não encontrado")
            return False
            
        except Exception as e:
            print(f"Erro ao validar CSV: {str(e)}")
            return False

    def importar(self):
        """Importa dados de todos os estados"""
        logger.info("Iniciando processo de importação")
        estados = [
            'PR', 'SC', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'AC', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'AL', 'SP', 'SE', 'TO'
        ]
        
        total_geral = {
            'estados_processados': 0,
            'removidos': 0,
            'atualizados': 0,
            'novos': 0,
            'estados_com_erro': []
        }
        
        for estado in estados:
            try:
                logger.info(f"\n=== Processando estado: {estado} ===")
                
                total_atualizados = 0
                total_removidos = 0
                total_novos = 0
                
                logger.info(f"Baixando dados do estado: {estado}")
                conteudo_csv = self._baixar_csv(self.base_url.format(estado))
                
                if not conteudo_csv:
                    logger.error(f"Erro: Não foi possível baixar dados para {estado}")
                    total_geral['estados_com_erro'].append((estado, "Falha ao baixar CSV"))
                    continue
                    
                logger.info("Dados baixados com sucesso!")
                logger.info("Processando CSV...")
                
                # Processar dados do CSV
                dados_novos = self._processar_csv(conteudo_csv)
                if not dados_novos:
                    logger.error(f"Erro: Nenhum imóvel encontrado para {estado}")
                    total_geral['estados_com_erro'].append((estado, "Nenhum imóvel encontrado"))
                    continue
                
                logger.info(f"Total de imóveis encontrados no CSV: {len(dados_novos)}")
                
                # Obter códigos dos imóveis do CSV
                codigos_novos = {item['N° do imóvel'] for item in dados_novos}
                
                # Buscar imóveis existentes na base
                from propriedades.models import Propriedade
                imoveis_existentes = Propriedade.objects.filter(estado=estado)
                logger.info(f"Total de imóveis existentes no banco: {imoveis_existentes.count()}")
                
                # Remover imóveis que não estão mais no CSV
                for imovel in imoveis_existentes:
                    if imovel.codigo not in codigos_novos:
                        logger.info(f"Removendo imóvel não mais disponível: {imovel.codigo}")
                        imovel.delete()
                        total_removidos += 1
                
                # Processar cada imóvel do CSV
                for item in dados_novos:
                    codigo = item['N° do imóvel']
                    imovel_existente = Propriedade.objects.filter(codigo=codigo).first()
                    
                    if imovel_existente:
                        logger.info(f"Imóvel existente encontrado: {codigo}")
                        # Verificar se precisa buscar a URL da imagem
                        if not imovel_existente.imagem_url:
                            logger.info(f"Imóvel {codigo} não possui URL de imagem. Buscando...")
                            url_imagem = self._obter_url_imagem(codigo)
                            if url_imagem:
                                imovel_existente.imagem_url = url_imagem
                                imovel_existente.save()
                                logger.info(f"URL da imagem atualizada para o imóvel {codigo}")
                    else:
                        # Importar novo imóvel
                        logger.info(f"Importando novo imóvel: {codigo}")
                        imovel_processado = self._processar_imovel(item)
                        if imovel_processado and self._salvar_imovel(imovel_processado):
                            total_novos += 1
                            logger.info(f"Novo imóvel importado com sucesso: {codigo}")
                
                # Atualizar totais gerais
                total_geral['atualizados'] += total_atualizados
                total_geral['removidos'] += total_removidos
                total_geral['novos'] += total_novos
                total_geral['estados_processados'] += 1
                
                # Relatório do estado
                logger.info(f"\n=== Relatório do Estado {estado} ===")
                logger.info(f"Total de imóveis removidos: {total_removidos}")
                logger.info(f"Total de imóveis atualizados (coordenadas): {total_atualizados}")
                logger.info(f"Total de imóveis novos: {total_novos}")
                
            except Exception as e:
                logger.error(f"\nErro ao processar estado {estado}: {str(e)}")
                total_geral['estados_com_erro'].append((estado, str(e)))
                import traceback
                logger.error(traceback.format_exc())
        
        # Relatório final geral
        logger.info("\n=== Relatório Final Geral ===")
        logger.info(f"Estados processados com sucesso: {total_geral['estados_processados']}")
        logger.info(f"Total geral de imóveis:")
        logger.info(f"- Removidos: {total_geral['removidos']}")
        logger.info(f"- Atualizados (coordenadas): {total_geral['atualizados']}")
        logger.info(f"- Novos: {total_geral['novos']}")
        if total_geral['estados_com_erro']:
            logger.error("\nEstados com erro:")
            for estado, erro in total_geral['estados_com_erro']:
                logger.error(f"- {estado}: {erro}")

def main():
    importador = ImportadorCaixa()
    importador.importar()

if __name__ == "__main__":
    main()