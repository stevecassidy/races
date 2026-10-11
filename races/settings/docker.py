#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
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

"""Settings for the docker-compose development stack (bin/docker.py).

The compose stack builds and runs the production image, so these settings must
not depend on development-only packages (no debug toolbar, no vcrpy).
"""

from races.settings.base import *

DEBUG = os.environ.get("DEBUG", "1") == "1"

# Compose supplies SECRET_KEY from .env.dev; fall back to a throwaway value so
# that a local stack boots without extra configuration.
SECRET_KEY = SECRET_KEY or "django-insecure-compose-development-key"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost 127.0.0.1 [::1]").split(" ")

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("SQL_DATABASE", "cabici"),
        "USER": os.environ.get("SQL_USER", "cabici"),
        "PASSWORD": os.environ.get("SQL_PASSWORD", "cabici"),
        "HOST": os.environ.get("SQL_HOST", "db"),
        "PORT": os.environ.get("SQL_PORT", "5432"),
    }
}

# email to the console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
