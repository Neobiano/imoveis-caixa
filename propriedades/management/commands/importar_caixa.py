import cloudinary.uploader
import requests
from io import BytesIO

class Command(BaseCommand):
    def process_property(self, property_data):
        # Processar imagem
        if property_data.get('imagem_url'):
            try:
                # Download da imagem
                response = requests.get(property_data['imagem_url'], timeout=10)
                if response.status_code == 200:
                    # Upload para o Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        BytesIO(response.content),
                        folder=f"imoveis/{property_data['estado']}/{property_data['cidade']}",
                        resource_type="image",
                        public_id=f"imovel_{property_data['codigo_imovel']}"
                    )
                    
                    # Salvar URLs do Cloudinary
                    property_data['imagem_cloudinary_url'] = upload_result['secure_url']
                    property_data['imagem_cloudinary_id'] = upload_result['public_id']
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"Imagem do imóvel {property_data['codigo_imovel']} enviada para o Cloudinary"
                    ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Erro ao processar imagem do imóvel {property_data['codigo_imovel']}: {str(e)}"
                )) 