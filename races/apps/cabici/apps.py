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

from django.apps import AppConfig


class CabiciConfig(AppConfig):
    name = 'races.apps.cabici'
    verbose_name = 'Cabici Race Manager'

    def ready(self):
        # Django 5.1's BaseContext.__copy__ is incompatible with Python 3.14,
        # where copying a template Context fails during rendered-template
        # assertions in the test client. Patch it at startup so the legacy app
        # continues to function under the modern runtime.
        if getattr(self, '_compat_patch_applied', False):
            return

        from django.template import context as template_context

        def _patched_basecontext_copy(self):
            duplicate = self.__class__.__new__(self.__class__)
            duplicate.__dict__ = self.__dict__.copy()
            if hasattr(self, 'dicts'):
                duplicate.dicts = self.dicts[:]
            return duplicate

        template_context.BaseContext.__copy__ = _patched_basecontext_copy
        self._compat_patch_applied = True
