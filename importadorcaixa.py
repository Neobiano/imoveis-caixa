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

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade, ImagemPropriedade

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('importacao.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

class ImportadorCaixa:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{}.csv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Carregar chaves da API do arquivo .env
        self.api_keys = [
            os.environ.get('HERE_API_KEY_1'),
            os.environ.get('HERE_API_KEY_2'),
            os.environ.get('HERE_API_KEY_3')
        ]
        self.current_api_key_index = 0
        logger.info("Iniciando nova sessão de importação")

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

    def _baixar_csv(self, estado):
        """Baixa o arquivo CSV para um estado específico"""
        try:
            url = self.base_url.format(estado)
            logger.info(f"\nTentando baixar CSV de: {url}")
            
            response = self.session.get(url, headers=self.headers)
            logger.info(f"Status da resposta: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Erro ao baixar dados. Status code: {response.status_code}")
                return None
            
            logger.info(f"Download realizado. Tamanho do conteúdo: {len(response.content)} bytes")
            
            # Tentar diferentes codificações
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    content = response.content.decode(encoding)
                    logger.info(f"Arquivo decodificado com sucesso usando {encoding}")
                    if len(content) > 0:
                        logger.debug(f"Primeiros 200 caracteres do conteúdo:")
                        logger.debug(content[:200])
                        return content
                except UnicodeDecodeError:
                    logger.warning(f"Falha ao decodificar com {encoding}")
                    continue
            
            if content is None:
                logger.error("ERRO: Não foi possível decodificar o arquivo com nenhuma codificação")
            return content
            
        except Exception as e:
            logger.error(f"ERRO ao baixar CSV para {estado}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _processar_csv(self, conteudo_csv):
        """Processa o conteúdo do CSV"""
        try:
            # Remover linhas vazias e espaços extras
            linhas = [linha for linha in conteudo_csv.splitlines() if linha.strip()]
            
            # Encontrar a linha do cabeçalho
            linha_cabecalho = None
            for i, linha in enumerate(linhas):
                if 'N° do imóvel' in linha:
                    linha_cabecalho = i
                    break
            
            if linha_cabecalho is None:
                logger.error("Cabeçalho não encontrado!")
                return []
            
            # Criar um novo CSV apenas com o cabeçalho e os dados
            csv_processado = StringIO()
            csv_processado.write(linhas[linha_cabecalho] + '\n')  # Cabeçalho
            
            # Adicionar apenas as linhas que têm dados
            for linha in linhas[linha_cabecalho + 1:]:
                if linha.strip() and ';' in linha:
                    csv_processado.write(linha + '\n')
            
            csv_processado.seek(0)
            
            # Usar DictReader para processar o CSV
            leitor = csv.DictReader(csv_processado, delimiter=';')
            
            # Processar as linhas
            dados = []
            for linha in leitor:
                # Limpar espaços em branco dos valores
                item = {k.strip(): v.strip() for k, v in linha.items() if k and k.strip()}
                if item:
                    logger.debug(f"Linha processada: {item}")
                    dados.append(item)
            
            logger.info(f"Total de imóveis encontrados: {len(dados)}")
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao processar CSV: {str(e)}")
            import traceback
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

    def _obter_coordenadas(self, endereco):
        """Obtém as coordenadas de um endereço usando o Here Maps API com rotação de APIs."""
        tentativas = 0
        apis_tentadas = set()

        while tentativas < len(self.api_keys):
            api_key = self.api_keys[self.current_api_key_index]
            if api_key in apis_tentadas:
                break

            try:
                url = f"https://geocode.search.hereapi.com/v1/geocode"
                params = {
                    'q': endereco,
                    'apiKey': api_key
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 429:  # Too Many Requests
                    logger.warning(f"API Key {api_key[:8]}... atingiu o limite. Tentando próxima API...")
                    apis_tentadas.add(api_key)
                    self.current_api_key_index = (self.current_api_key_index + 1) % len(self.api_keys)
                    tentativas += 1
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                if data['items']:
                    position = data['items'][0]['position']
                    return position['lat'], position['lng']
                return None, None

            except requests.exceptions.RequestException as e:
                if "429" in str(e):  # Too Many Requests em caso de exceção
                    logger.warning(f"API Key {api_key[:8]}... atingiu o limite. Tentando próxima API...")
                    apis_tentadas.add(api_key)
                    self.current_api_key_index = (self.current_api_key_index + 1) % len(self.api_keys)
                    tentativas += 1
                    continue
                logger.error(f"Erro na API do Here Maps: {str(e)}")
                return None, None

        if tentativas == len(self.api_keys):
            logger.error("Todas as APIs do Here Maps atingiram o limite de requisições")
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
            logger.info(f"\nProcessando novo imóvel: {dados.get('N° do imóvel', 'sem código')}")
            # Imprimir os dados para debug
            logger.debug(f"Dados do imóvel: {dados}")
            
            # Extrair o código do imóvel (campo obrigatório)
            codigo = dados.get('N° do imóvel', '').strip()
            if not codigo:
                logger.warning("Imóvel sem código, ignorando...")
                return None

            # Extrair área e quartos da descrição
            descricao = dados.get('Descrição', '').strip()
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
            except:
                desconto = Decimal('0')
            logger.info(f"Desconto: {desconto}%")

            endereco = dados.get('Endereço', '').strip()
            cidade = dados.get('Cidade', '').strip()
            estado = dados.get('UF', '').strip()

            # Montar o objeto do imóvel
            imovel = {
                'codigo': codigo,
                'tipo': 'Residencial',  # Valor padrão
                'tipo_imovel': tipo_imovel,
                'endereco': endereco,
                'bairro': dados.get('Bairro', '').strip(),
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
                'link': dados.get('Link de acesso', '').strip()
            }

            print(f"Processando imóvel: {imovel['codigo']}")
            # Agora vamos coletar coordenadas apenas para imóveis novos
            endereco_completo = f"{endereco}, {cidade}, {estado}, Brasil"
            latitude, longitude = self._obter_coordenadas(endereco_completo)
            imovel['latitude'] = latitude
            imovel['longitude'] = longitude
            if latitude and longitude:
                logger.info(f"Coordenadas obtidas: Latitude={latitude}, Longitude={longitude}")
            else:
                logger.warning(f"Não foi possível obter coordenadas para o imóvel {imovel['codigo']}")

            # Obter URL da imagem usando apenas o código
            logger.info(f"Buscando imagem para o imóvel {codigo}")
            imovel['imagem_url'] = self._obter_url_imagem(codigo)
            if imovel['imagem_url']:
                logger.info(f"URL da imagem encontrada: {imovel['imagem_url']}")
            else:
                logger.warning(f"Nenhuma imagem encontrada para o imóvel {codigo}")

            logger.info(f"Imóvel processado com sucesso: {codigo}")
            return imovel
            
        except Exception as e:
            logger.error(f"Erro ao processar dados do imóvel: {str(e)}")
            import traceback
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
                conteudo_csv = self._baixar_csv(estado)
                
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
                
                # 1.2 Remover imóveis que não estão mais no CSV
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

                        # Atualizar coordenadas se estiverem faltando
                        if imovel_existente.latitude is None or imovel_existente.longitude is None:
                            logger.info(f"Atualizando coordenadas do imóvel: {codigo}")
                            endereco_completo = f"{item.get('Endereço', '')}, {item.get('Cidade', '')}, {item.get('UF', '')}, Brasil"
                            latitude, longitude = self._obter_coordenadas(endereco_completo)
                            if latitude and longitude:
                                imovel_existente.latitude = latitude
                                imovel_existente.longitude = longitude
                                imovel_existente.save()
                                logger.info(f"Coordenadas atualizadas: lat={latitude}, lng={longitude}")
                                total_atualizados += 1
                            else:
                                logger.warning(f"Não foi possível obter coordenadas para o imóvel {codigo}")
                    else:
                        # 1.3 Importar novo imóvel
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