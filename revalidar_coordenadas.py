import os
import django
import logging
from decimal import Decimal
from dotenv import load_dotenv
from validacao_geografica import ValidadorGeografico
from importadorcaixa import ImportadorCaixa

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('revalidacao_coordenadas.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RevalidadorCoordenadas:
    def __init__(self):
        """Inicializa o revalidador com o validador geográfico e importador."""
        self.validador = ValidadorGeografico()
        self.importador = ImportadorCaixa()
        logger.info("Revalidador de Coordenadas inicializado")

    def validar_coordenadas_existentes(self):
        """Valida e atualiza coordenadas dos imóveis."""
        logger.info("Iniciando validação de coordenadas existentes")
        
        # Buscar apenas imóveis com latitude e longitude preenchidas
        imoveis_com_coordenadas = Propriedade.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        )
        
        total_imoveis = imoveis_com_coordenadas.count()
        logger.info(f"Total de imóveis com coordenadas: {total_imoveis}")
        
        total = {
            'validos': 0,
            'invalidos': 0,
            'atualizados_api': 0,
            'atualizados_aleatorio': 0,
            'erros': 0
        }
        
        try:
            for imovel in imoveis_com_coordenadas:
                try:
                    # Converter coordenadas para float
                    lat = float(imovel.latitude)
                    lon = float(imovel.longitude)
                    
                    # Validar se as coordenadas estão dentro do município
                    lat_validada, lon_validada = self.validador.validar_coordenadas(
                        lat=lat,
                        lon=lon,
                        cidade=imovel.cidade,
                        uf=imovel.estado
                    )
                    
                    # Se as coordenadas mudaram, são inválidas
                    if lat != lat_validada or lon != lon_validada:
                        logger.info(f"\nImóvel {imovel.codigo} em {imovel.cidade}/{imovel.estado}")
                        logger.info(f"Coordenadas atuais: {lat}, {lon}")
                        
                        # Tentar obter novas coordenadas da API
                        lat_api, lon_api = self.importador._obter_coordenadas(
                            endereco=imovel.endereco,
                            cidade=imovel.cidade,
                            estado=imovel.estado
                        )
                        
                        if lat_api and lon_api:
                            # Validar coordenadas da API
                            lat_validada, lon_validada = self.validador.validar_coordenadas(
                                lat=lat_api,
                                lon=lon_api,
                                cidade=imovel.cidade,
                                uf=imovel.estado
                            )
                            
                            if lat_api == lat_validada and lon_api == lon_validada:
                                # Coordenadas da API são válidas
                                logger.info(f"Coordenadas da API válidas: {lat_api}, {lon_api}")
                                imovel.latitude = Decimal(str(lat_api))
                                imovel.longitude = Decimal(str(lon_api))
                                total['atualizados_api'] += 1
                            else:
                                # Coordenadas da API são inválidas, usar coordenadas aleatórias
                                logger.info(f"Coordenadas da API inválidas, usando aleatórias: {lat_validada}, {lon_validada}")
                                imovel.latitude = Decimal(str(lat_validada))
                                imovel.longitude = Decimal(str(lon_validada))
                                total['atualizados_aleatorio'] += 1
                        else:
                            # API falhou, usar coordenadas aleatórias
                            logger.info(f"API falhou, usando coordenadas aleatórias: {lat_validada}, {lon_validada}")
                            imovel.latitude = Decimal(str(lat_validada))
                            imovel.longitude = Decimal(str(lon_validada))
                            total['atualizados_aleatorio'] += 1
                        
                        imovel.save()
                        total['invalidos'] += 1
                    else:
                        total['validos'] += 1
                    
                    # Log de progresso a cada 100 imóveis
                    if (total['validos'] + total['invalidos']) % 100 == 0:
                        logger.info(f"Progresso: {total['validos'] + total['invalidos']}/{total_imoveis}")
                        
                except Exception as e:
                    logger.error(f"Erro ao validar imóvel {imovel.codigo}: {str(e)}")
                    total['erros'] += 1
                    
        except Exception as e:
            logger.error(f"Erro durante a validação: {str(e)}")
            
        # Relatório final
        logger.info("\n=== Relatório Final ===")
        logger.info(f"Total de imóveis com coordenadas: {total_imoveis}")
        logger.info(f"Coordenadas válidas: {total['validos']}")
        logger.info(f"Coordenadas inválidas: {total['invalidos']}")
        logger.info(f"Atualizados via API: {total['atualizados_api']}")
        logger.info(f"Atualizados com coordenadas aleatórias: {total['atualizados_aleatorio']}")
        logger.info(f"Erros: {total['erros']}")

def main():
    revalidador = RevalidadorCoordenadas()
    revalidador.validar_coordenadas_existentes()

if __name__ == "__main__":
    main() 