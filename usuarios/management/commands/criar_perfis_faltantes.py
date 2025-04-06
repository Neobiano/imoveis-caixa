from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from usuarios.models import PerfilUsuario

class Command(BaseCommand):
    help = 'Cria perfis de usuário para usuários que não têm perfil'

    def handle(self, *args, **options):
        usuarios_sem_perfil = User.objects.filter(perfilusuario__isnull=True)
        total = usuarios_sem_perfil.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Todos os usuários já têm perfil!'))
            return
            
        for user in usuarios_sem_perfil:
            PerfilUsuario.objects.create(usuario=user)
            self.stdout.write(self.style.SUCCESS(f'Perfil criado para {user.username}'))
            
        self.stdout.write(self.style.SUCCESS(f'Total de perfis criados: {total}')) 