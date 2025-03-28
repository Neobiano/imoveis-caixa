import os
import django
import logging
from decimal import Decimal

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('correcao_urls.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def corrigir_url_imagem(codigo):
    """Gera a URL correta da imagem usando o padrão F{id_imovel}21 com padding de zeros"""
    try:
        # Garantir que o código tenha 13 dígitos (preenchendo com zeros à esquerda)
        codigo_padded = str(codigo).zfill(13)
        return f"https://venda-imoveis.caixa.gov.br/fotos/F{codigo_padded}21.jpg"
    except Exception as e:
        logger.error(f"Erro ao gerar URL para o código {codigo}: {str(e)}")
        return None

def main():
    """Corrige as URLs das imagens de todos os imóveis na base"""
    logger.info("Iniciando processo de correção das URLs das imagens")
    
    # Contadores para o relatório
    total_imoveis = 0
    urls_corrigidas = 0
    urls_invalidas = 0
    
    try:
        # Buscar todos os imóveis
        imoveis = Propriedade.objects.all()
        total_imoveis = imoveis.count()
        logger.info(f"Total de imóveis encontrados: {total_imoveis}")
        
        for imovel in imoveis:
            try:
                # Gerar a nova URL
                nova_url = corrigir_url_imagem(imovel.codigo)
                
                if nova_url:
                    # Verificar se a URL atual está no formato antigo ou ausente
                    url_atual = imovel.imagem_url or ''
                    if not url_atual or len(url_atual.split('F')[-1].split('.')[0]) != 15:  # 13 dígitos + "21"
                        # Atualizar a URL
                        imovel.imagem_url = nova_url
                        imovel.save()
                        logger.info(f"URL corrigida para o imóvel {imovel.codigo}")
                        logger.info(f"  Antiga: {url_atual}")
                        logger.info(f"  Nova: {nova_url}")
                        urls_corrigidas += 1
                else:
                    logger.warning(f"Não foi possível gerar URL para o imóvel {imovel.codigo}")
                    urls_invalidas += 1
                    
            except Exception as e:
                logger.error(f"Erro ao processar imóvel {imovel.codigo}: {str(e)}")
                urls_invalidas += 1
                continue
        
        # Relatório final
        logger.info("\n=== Relatório Final ===")
        logger.info(f"Total de imóveis processados: {total_imoveis}")
        logger.info(f"URLs corrigidas com sucesso: {urls_corrigidas}")
        logger.info(f"URLs com erro: {urls_invalidas}")
        
    except Exception as e:
        logger.error(f"Erro durante o processo de correção: {str(e)}")
        return

if __name__ == "__main__":
    main() 