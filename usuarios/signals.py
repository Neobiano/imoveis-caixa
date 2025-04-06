from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import PerfilUsuario

@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    """Cria ou atualiza o perfil do usuário quando um usuário é criado/atualizado"""
    if created:
        PerfilUsuario.objects.create(usuario=instance)
    else:
        # Garantir que o usuário tenha um perfil mesmo se não foi criado no signal
        PerfilUsuario.objects.get_or_create(usuario=instance) 