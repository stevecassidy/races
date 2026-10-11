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

"""Settings for the automated test suite (bin/runtests.py)."""

from races.settings.development import *

# Tests never collect static assets, so avoid the manifest/hash based storage
# backends and use plain filesystem lookup.
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Tests never serve static assets, so drop WhiteNoise from the middleware
# stack (it warns about a missing staticfiles directory otherwise).
MIDDLEWARE = tuple(m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware")

# Speed up password hashing in tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
