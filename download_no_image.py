import requests
import os

def download_no_image():
    # URL de uma imagem padrão do Unsplash
    url = "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=500&auto=format&fit=crop"
    
    # Caminho para salvar a imagem
    save_path = os.path.join('propriedades', 'static', 'img', 'no-image.jpg')
    
    # Criar diretório se não existir
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    try:
        # Baixar a imagem
        response = requests.get(url)
        response.raise_for_status()
        
        # Salvar a imagem
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Imagem baixada com sucesso para {save_path}")
    except Exception as e:
        print(f"Erro ao baixar a imagem: {e}")

if __name__ == "__main__":
    download_no_image() 