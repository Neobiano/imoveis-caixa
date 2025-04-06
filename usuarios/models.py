from django.db import models
from django.contrib.auth.models import User
from propriedades.models import Propriedade

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    google_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    ultimo_acesso = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.usuario.username

class PreferenciasUsuario(models.Model):
    TIPO_CHOICES = [
        ('casa', 'Casa'),
        ('apartamento', 'Apartamento'),
        ('terreno', 'Terreno'),
        ('comercial', 'Comercial'),
    ]

    usuario = models.OneToOneField(PerfilUsuario, on_delete=models.CASCADE)
    tipo_imovel = models.CharField(max_length=20, choices=TIPO_CHOICES, null=True, blank=True)
    preco_minimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preco_maximo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=2, null=True, blank=True)
    area_minima = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_maxima = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notificacoes_ativas = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferências de {self.usuario.usuario.username}"

class Favorito(models.Model):
    usuario = models.ForeignKey(PerfilUsuario, on_delete=models.CASCADE)
    propriedade = models.ForeignKey(Propriedade, on_delete=models.CASCADE)
    data_adicao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('usuario', 'propriedade')

    def __str__(self):
        return f"{self.usuario.usuario.username} - {self.propriedade.codigo}"
