from .base import *
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# PostgreSQL — Railway pe DATABASE_URL automatically milti hai
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}

# Brevo SMTP — free 300 emails/day
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp-relay.brevo.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Sirf apna frontend domain
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')

# Security headers — production mein zaroori
SECURE_SSL_REDIRECT            = True
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
SECURE_HSTS_SECONDS            = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_BROWSER_XSS_FILTER      = True
X_FRAME_OPTIONS                = 'DENY'
