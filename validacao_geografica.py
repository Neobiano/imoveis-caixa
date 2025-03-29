import json
import logging
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union
import numpy as np
from difflib import get_close_matches
import unidecode
import re

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validacao_geografica.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ValidadorGeografico:
    def __init__(self, caminho_geojson='importador/data/municipios.geojson'):
        """Inicializa o validador com o arquivo GeoJSON dos municípios."""
        self.municipios = self._carregar_geojson(caminho_geojson)
        self.cache_municipios = {}  # Cache para polígonos já processados
        logger.info("Validador Geográfico inicializado com sucesso")

    def _carregar_geojson(self, caminho):
        """Carrega o arquivo GeoJSON dos municípios."""
        with open(caminho, 'r', encoding='utf-8-sig') as f:
            return json.load(f)

    def _normalizar_texto(self, texto):
        """Normaliza o texto para comparação."""
        if not texto:
            return ""
        # Remove acentos e converte para maiúsculo
        texto = unidecode.unidecode(texto.upper())
        # Remove caracteres especiais
        texto = re.sub(r'[^A-Z0-9\s]', '', texto)
        return texto

    def _encontrar_municipio_similar(self, nome_cidade, uf):
        """Encontra o município mais similar dentro da UF especificada."""
        nome_normalizado = self._normalizar_texto(nome_cidade)
        
        # Filtrar municípios da UF
        municipios_uf = [
            feature for feature in self.municipios['features']
            if feature['properties']['UF'] == uf
        ]
        
        # Criar lista de nomes normalizados para comparação
        nomes_municipios = [self._normalizar_texto(m['properties']['name']) for m in municipios_uf]
        
        # Encontrar o match mais próximo
        matches = get_close_matches(nome_normalizado, nomes_municipios, n=1, cutoff=0.6)
        
        if matches:
            # Encontrar o feature correspondente
            idx = nomes_municipios.index(matches[0])
            return municipios_uf[idx]
        
        return None

    def _ponto_dentro_poligono(self, lat, lon, poligono):
        """Verifica se um ponto está dentro de um polígono."""
        ponto = Point(lon, lat)  # GeoJSON usa (lon, lat)
        return poligono.contains(ponto)

    def _gerar_ponto_aleatorio_no_poligono(self, poligono):
        """Gera um ponto aleatório dentro do polígono do município."""
        minx, miny, maxx, maxy = poligono.bounds
        
        while True:
            lon = np.random.uniform(minx, maxx)
            lat = np.random.uniform(miny, maxy)
            ponto = Point(lon, lat)
            
            if poligono.contains(ponto):
                return lat, lon

    def validar_coordenadas(self, lat, lon, cidade, uf):
        """
        Valida as coordenadas recebidas e retorna coordenadas válidas.
        
        Args:
            lat (float): Latitude recebida da API
            lon (float): Longitude recebida da API
            cidade (str): Nome da cidade do imóvel
            uf (str): UF do imóvel
            
        Returns:
            tuple: (latitude, longitude) válidas para o município
        """
        try:
            # Identificar o município no GeoJSON
            municipio = self._encontrar_municipio_similar(cidade, uf)
            if not municipio:
                logger.error(f"Município não encontrado: {cidade}/{uf}")
                return None, None

            # Criar chave para cache
            cache_key = f"{cidade}_{uf}"
            
            # Verificar se o polígono já está em cache
            if cache_key not in self.cache_municipios:
                # Converter geometria para objeto Shapely
                geometria = shape(municipio['geometry'])
                if isinstance(geometria, Polygon):
                    poligono = geometria
                else:  # MultiPolygon ou outro tipo
                    poligono = unary_union(geometria)
                self.cache_municipios[cache_key] = poligono
            else:
                poligono = self.cache_municipios[cache_key]

            # Verificar se as coordenadas estão dentro do município
            if lat is not None and lon is not None:
                if self._ponto_dentro_poligono(lat, lon, poligono):
                    logger.info(f"Coordenadas {lat}, {lon} válidas para {cidade}/{uf}")
                    return lat, lon
                else:
                    logger.warning(f"Coordenadas {lat}, {lon} fora do município {cidade}/{uf}")

            # Gerar novas coordenadas dentro do município
            nova_lat, nova_lon = self._gerar_ponto_aleatorio_no_poligono(poligono)
            logger.info(f"Novas coordenadas geradas para {cidade}/{uf}: {nova_lat}, {nova_lon}")
            return nova_lat, nova_lon

        except Exception as e:
            logger.error(f"Erro ao validar coordenadas: {str(e)}")
            return None, None

# Exemplo de uso:
if __name__ == "__main__":
    validador = ValidadorGeografico()
    
    # Teste com o caso mencionado
    lat, lon = validador.validar_coordenadas(
        lat=-23.447380,
        lon=-46.686700,
        cidade="BRASILANDIA",
        uf="MS"
    )
    print(f"Coordenadas validadas: {lat}, {lon}") 