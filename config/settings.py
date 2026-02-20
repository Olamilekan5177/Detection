import os
from pathlib import Path

# Initialize environment variables - make optional
try:
    import environ
    env = environ.Env()
    environ.Env.read_env()
except ImportError:
    # Create a simple env substitute
    class Env:
        def __call__(self, key, default=None):
            return os.environ.get(key, default)
    env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Development settings
DEBUG = True
ALLOWED_HOSTS = ['*']  # For development - restrict in production

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-only-for-development')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.gis',  # For spatial data - enable with PostGIS
    
    # Third party
    'rest_framework',
    'corsheaders',
    # 'leaflet',  # For map visualization - optional
    # 'django_celery_beat',  # For scheduled tasks - optional
    
    # Local apps
    'detection',
    'dashboard',
    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': [
                'dashboard.templatetags.math_filters',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# For production with PostGIS:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.contrib.gis.db.backends.postgis',
#         'NAME': env('DB_NAME', default='oil_spill_db'),
#         'USER': env('DB_USER', default='postgres'),
#         'PASSWORD': env('DB_PASSWORD', default='password'),
#         'HOST': env('DB_HOST', default='localhost'),
#         'PORT': env('DB_PORT', default='5432'),
#     }
# }

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Beat Schedule - for automated satellite data processing
# Install: pip install django-celery-beat
# Run: celery -A config beat -l info
CELERY_BEAT_SCHEDULE = {
    'process-satellite-every-6-hours': {
        'task': 'detection.tasks.process_real_satellite_data',
        'schedule': 21600.0,  # 6 hours in seconds
        'kwargs': {'region_id': 2},  # Niger Delta region
    },
    'check-monitoring-regions-every-1-hour': {
        'task': 'detection.tasks.check_monitoring_region',
        'schedule': 3600.0,  # 1 hour in seconds
        'kwargs': {'region_id': 2},
    },
    'send-alerts-every-30-minutes': {
        'task': 'detection.tasks.send_alerts',
        'schedule': 1800.0,  # 30 minutes in seconds
    },
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# STATICFILES_DIRS = [BASE_DIR / 'static']  # Optional for development

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ML Model settings
ML_MODEL_PATH = BASE_DIR / 'ml_models/saved_models/oil_spill_detector.h5'
IMAGE_SIZE = (256, 256)  # Input size for CNN
DETECTION_THRESHOLD = 0.7  # Confidence threshold

# Sentinel Hub API (get free API key from Copernicus)
SENTINEL_API_USERNAME = env('SENTINEL_API_USERNAME', default='')
SENTINEL_API_PASSWORD = env('SENTINEL_API_PASSWORD', default='')

# Authentication
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard:monitoring'
LOGOUT_REDIRECT_URL = 'login'