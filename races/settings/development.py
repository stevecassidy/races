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

"""Local development settings (bin/develop.py)."""

from races.settings.base import *

DEBUG = True

# Throwaway key for local runs only. Never used in production, where the key
# must come from the environment (see production.py).
SECRET_KEY = SECRET_KEY or "django-insecure-local-development-key"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost 127.0.0.1 [::1]").split(" ")

DATABASES["default"]["NAME"] = "races_development"

# email to the console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Debug toolbar is a development-only dependency (requirements/dev.txt), so it
# is wired up here rather than in the shared base settings.
INSTALLED_APPS += ("debug_toolbar",)
MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
