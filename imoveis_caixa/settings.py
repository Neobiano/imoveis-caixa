import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Carregar variáveis de ambiente
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Identificar o ambiente
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
IS_DEVELOPMENT = ENVIRONMENT == 'development'
IS_PRODUCTION = ENVIRONMENT == 'production'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Configuração de hosts permitidos baseada no ambiente
if IS_PRODUCTION:
    ALLOWED_HOSTS = ['imoveis-caixa.onrender.com']
    CSRF_TRUSTED_ORIGINS = ['https://imoveis-caixa.onrender.com']
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'propriedades',
    'usuarios',
    'django.contrib.sites',  # Necessário para allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para arquivos estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Necessário para allauth
]

# Configuração de templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Configuração de URLs
ROOT_URLCONF = 'imoveis_caixa.urls'

# Configuração do banco de dados baseada no ambiente
if IS_DEVELOPMENT:
    # URL padrão para desenvolvimento local
    DEFAULT_DATABASE_URL = 'postgres://gerente:1234@localhost:5432/imoveis'
else:
    # Em produção, não definimos URL padrão - deve vir das variáveis de ambiente
    DEFAULT_DATABASE_URL = None

DATABASES = {
    'default': dj_database_url.config(
        default=DEFAULT_DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Configurações de arquivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuração do WhiteNoise apenas em produção
if IS_PRODUCTION:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
else:
    # Em desenvolvimento, não precisamos do WhiteNoise
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Configurações de segurança apenas em produção
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações de performance para PostgreSQL
if 'postgresql' in DATABASES['default']['ENGINE']:
    DATABASES['default']['OPTIONS'] = {
        'client_encoding': 'UTF8',
        'connect_timeout': 10,
    }

# Configurações das APIs
HERE_API_KEY_1 = os.environ.get('HERE_API_KEY_1')
HERE_API_KEY_2 = os.environ.get('HERE_API_KEY_2')
HERE_API_KEY_3 = os.environ.get('HERE_API_KEY_3')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Configurações do Google OAuth
if IS_DEVELOPMENT:
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID_DEV')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET_DEV')
else:
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID_PROD')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET_PROD')

# Configurações de Autenticação
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Configurações do Django-allauth
SITE_ID = 1

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_CLIENT_ID,
            'secret': GOOGLE_CLIENT_SECRET,
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

# Configurações do Allauth
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

# URLs de redirecionamento
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/' 