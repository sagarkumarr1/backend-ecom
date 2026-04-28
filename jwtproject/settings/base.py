from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY .env mein set karo!")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'axes',
    'corsheaders',
    'django_filters',

    # Our apps
    'jwtapp',
    'products',
    'cart',
    'orders',
    'payments',
    'reviews',
]

AUTH_USER_MODEL = 'jwtapp.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'jwtproject.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'jwtproject.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'jwtapp.backends.EmailOrMobileBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE      = 'en-us'
TIME_ZONE          = 'Asia/Kolkata'
USE_I18N           = True
USE_TZ             = True
STATIC_URL         = 'static/'
STATIC_ROOT        = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'jwtapp.utils.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '200/minute',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES':        ('Bearer',),
    'UPDATE_LAST_LOGIN':        True,
}

AXES_FAILURE_LIMIT      = 5
AXES_COOLOFF_TIME       = 1
AXES_RESET_ON_SUCCESS   = True
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']

SPECTACULAR_SETTINGS = {
    'TITLE':       'Ecommerce API',
    'DESCRIPTION': 'Customer · Vendor · Admin — JWT Auth + Ecommerce Backend',
    'VERSION':     '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

GOOGLE_OAUTH2_CLIENT_ID = os.environ.get('GOOGLE_OAUTH2_CLIENT_ID', '')

# ─── Razorpay ─────────────────────────────────────────────────
RAZORPAY_KEY_ID         = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET     = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')

# ─── Cloudinary ───────────────────────────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY':    os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}
