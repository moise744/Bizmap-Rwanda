# config/settings/development.py
from .base import *
import os
import environ

# ===============================
# Environment
# ===============================
env = environ.Env()

# Read .env file if it exists
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    environ.Env.read_env(env_file)

# Debug
DEBUG = env.bool("DEBUG", default=True)

# Allowed hosts
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost", "0.0.0.0"])

# ===============================
# Database (PostgreSQL)
# ===============================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='busimap_rwanda'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='simplepass'),
        'HOST': env('DB_HOST', default='127.0.0.1'),
        'PORT': env('DB_PORT', default='5432'),
        'OPTIONS': {'connect_timeout': 60},
        'CONN_MAX_AGE': 0,
    }
}

# ===============================
# Debug Toolbar
# ===============================
if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
    except ImportError:
        pass

# ===============================
# Email Configuration (Gmail SMTP)
# ===============================
# Only for development: use Gmail SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="your-email@gmail.com")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="your-16-char-app-password")
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default=f"BusiMap Rwanda <{EMAIL_HOST_USER}>"
)

# ===============================
# Security (Development)
# ===============================
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)

# ===============================
# CORS
# ===============================
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
])

# ===============================
# Redis + Celery + Channels
# ===============================
REDIS_AVAILABLE = True
try:
    import redis
    redis_url = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
    r = redis.Redis.from_url(redis_url)
    r.ping()
    
    # Cache
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }

    # Celery
    CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
    CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/0")

    # Channels
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [redis_url]},
        },
    }

except Exception as e:
    REDIS_AVAILABLE = False
    print(f"WARNING: Redis not available ({e}), using fallback configurations")

    # Fallback cache
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}

    # Make Celery run synchronously
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

    # Fallback channels
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}

# ===============================
# Elasticsearch (Development optional)
# ===============================
try:
    elasticsearch_url = env('ELASTICSEARCH_URL', default='')
    if elasticsearch_url:
        ELASTICSEARCH_DSL = {'default': {'hosts': elasticsearch_url}}
except:
    pass

# ===============================
# Logging
# ===============================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django_dev.log',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO')},
    'loggers': {
        'django.db.backends': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'apps': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
    },
}

# ===============================
# Static & Media (Development)
# ===============================
STATICFILES_DIRS = [BASE_DIR / 'assets']
STATIC_ROOT = BASE_DIR / 'staticfiles'

(BASE_DIR / 'media').mkdir(exist_ok=True)
(BASE_DIR / 'logs').mkdir(exist_ok=True)
(BASE_DIR / 'assets').mkdir(exist_ok=True)

# ===============================
# Print Development Info
# ===============================
print("=== DEVELOPMENT MODE ===")
print(f"DEBUG: {DEBUG}")
print(f"Database: {DATABASES['default']['HOST']}:{DATABASES['default']['PORT']}")
print(f"Redis Available: {REDIS_AVAILABLE}")
print("========================")
