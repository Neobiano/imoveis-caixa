from django.db import models

# Create your models here.

class Propriedade(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=100)
    tipo_imovel = models.CharField(max_length=50, null=True, blank=True, help_text="Tipo extraído da descrição (Casa, Apartamento, Terreno, etc)")
    endereco = models.TextField()
    cidade = models.CharField(max_length=100, db_index=True)
    estado = models.CharField(max_length=2, db_index=True)
    bairro = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    valor_avaliacao = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    desconto = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    descricao = models.TextField()
    modalidade_venda = models.CharField(max_length=100, null=True, blank=True)
    area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_privativa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_terreno = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quartos = models.IntegerField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitude do imóvel")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitude do imóvel")
    imagem_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL da imagem do imóvel no site da Caixa"
    )

    def __str__(self):
        return f"{self.codigo} - {self.endereco}"

    class Meta:
        verbose_name = "Propriedade"
        verbose_name_plural = "Propriedades"

class ImagemPropriedade(models.Model):
    propriedade = models.ForeignKey(Propriedade, on_delete=models.CASCADE, related_name='imagens')
    url = models.URLField()
    ordem = models.IntegerField(default=0)

    def __str__(self):
        return f"Imagem {self.ordem} - {self.propriedade.codigo}"

    class Meta:
        verbose_name = "Imagem da Propriedade"
        verbose_name_plural = "Imagens da Propriedade"
        ordering = ['ordem']
