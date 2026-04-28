from .base import *

DEBUG         = True
ALLOWED_HOSTS = ['*']

# SQLite — dev mein fast, PostgreSQL install ki zaroorat nahi
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Emails console pe print hongi — inbox check karne ki zaroorat nahi
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Dev mein sab frontend origins allow
CORS_ALLOW_ALL_ORIGINS = True
