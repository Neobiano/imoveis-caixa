import os
import django
import logging
from dotenv import load_dotenv

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('atualizacao_matriculas.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def atualizar_urls_matriculas():
    """Atualiza as URLs das matrículas para todos os imóveis existentes."""
    logger.info("Iniciando atualização das URLs das matrículas")
    
    # Buscar todos os imóveis
    imoveis = Propriedade.objects.all()
    total = imoveis.count()
    logger.info(f"Total de imóveis para processar: {total}")
    
    atualizados = 0
    erros = 0
    
    try:
        for imovel in imoveis:
            try:
                # Gerar URL da matrícula
                if imovel.codigo and imovel.estado:
                    # Formatar o código com zeros à esquerda se necessário
                    codigo_formatado = str(imovel.codigo).zfill(13)
                    matricula_url = f"https://venda-imoveis.caixa.gov.br/editais/matricula/{imovel.estado}/{codigo_formatado}.pdf"
                    
                    # Atualizar apenas se a URL for diferente
                    if imovel.matricula_url != matricula_url:
                        imovel.matricula_url = matricula_url
                        imovel.save()
                        atualizados += 1
                        logger.info(f"Imóvel {imovel.codigo} atualizado com URL: {matricula_url}")
                
                # Log de progresso a cada 100 imóveis
                if (atualizados + erros) % 100 == 0:
                    logger.info(f"Progresso: {atualizados + erros}/{total}")
                    
            except Exception as e:
                logger.error(f"Erro ao processar imóvel {imovel.codigo}: {str(e)}")
                erros += 1
                
    except Exception as e:
        logger.error(f"Erro durante a atualização: {str(e)}")
        
    # Relatório final
    logger.info("\n=== Relatório Final ===")
    logger.info(f"Total de imóveis processados: {total}")
    logger.info(f"Imóveis atualizados: {atualizados}")
    logger.info(f"Erros: {erros}")

def main():
    atualizar_urls_matriculas()

if __name__ == "__main__":
    main() 