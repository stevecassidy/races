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

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("SQL_DATABASE", "cabici"),
        "USER": os.environ.get("SQL_USER", "cabici"),
        "OPTIONS": {
            "passfile": ".pgpass",
        }
    }
}



# email to the console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

GEOPOSITION_GOOGLE_MAPS_API_KEY = os.environ.get("GEOPOSITION_GOOGLE_MAPS_API_KEY")
GOOGLE_MAPS_API_KEY = GEOPOSITION_GOOGLE_MAPS_API_KEY
