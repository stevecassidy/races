from races.settings.base import *

DEBUG = False
TEMPLATE_DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'cabici_pg',
        'USER': 'cabici_pg',
        'PASSWORD': 'pigeon59',
        'HOST': '',
        'PORT': '',
    }
}
