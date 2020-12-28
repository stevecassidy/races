from races.settings.base import *

DEBUG = os.environ.get("DEBUG")
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("SQL_DATABASE", os.path.join(BASE_DIR, "db.sqlite3")),
        "USER": os.environ.get("SQL_USER", "user"),
        "PASSWORD": os.environ.get("SQL_PASSWORD", "password"),
        "HOST": os.environ.get("SQL_HOST", "localhost"),
        "PORT": os.environ.get("SQL_PORT", "5432"),
    }
}

SECRET_KEY = os.environ.get("SECRET_KEY")

# 'DJANGO_ALLOWED_HOSTS' should be a single string of hosts with a space between each.
# For example: 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS").split(" ")


GEOPOSITION_GOOGLE_MAPS_API_KEY = os.environ.get("GEOPOSITION_GOOGLE_MAPS_API_KEY")
GOOGLE_MAPS_API_KEY = GEOPOSITION_GOOGLE_MAPS_API_KEY

