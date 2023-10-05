#!/usr/bin/python
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from races.settings.base import *

DEBUG = os.environ.get("DEBUG") == "1"
TEMPLATE_DEBUG = DEBUG
print("DEBUG", DEBUG, os.environ.get("DEBUG"))

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

SECRET_KEY = os.environ.get("SECRET_KEY", "really_secret")

# 'DJANGO_ALLOWED_HOSTS' should be a single string of hosts with a space between each.
# For example: 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(" ")
CSRF_TRUSTED_ORIGINS = ['https://cabici.waratahmasters.com.au']

GEOPOSITION_GOOGLE_MAPS_API_KEY = os.environ.get("GEOPOSITION_GOOGLE_MAPS_API_KEY")
GOOGLE_MAPS_API_KEY = GEOPOSITION_GOOGLE_MAPS_API_KEY

DEFAULT_FROM_EMAIL = os.environ.get("ADMIN_EMAIL")
SERVER_EMAIL = os.environ.get("ADMIN_EMAIL")

ADMINS = (
    ('Steve Cassidy', os.environ.get("ADMIN_EMAIL")),
)

# django-anymail configuration
ANYMAIL = {
     "MAILERSEND_API_TOKEN": os.environ.get("MAILERSEND_API_TOKEN"),
}
EMAIL_BACKEND = "anymail.backends.mailersend.EmailBackend"

# Saving JSON result uploads for debugging
SAVE_RESULT_UPLOADS = True
SAVE_RESULT_UPLOADS_DIR = '/var/lib/cabici/cabici-uploads'

STATIC_ROOT = '/var/lib/cabici/staticfiles'

# enable whitenoise handling of static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
