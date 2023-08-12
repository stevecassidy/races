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

from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class TidyHQAccount(ProviderAccount):

    def to_str(self):
        dflt = super(TidyHQAccount, self).to_str()
        return '%s (%s)' % (
            self.account.extra_data.get('name', ''),
            dflt,
        )


class TidyHQProvider(OAuth2Provider):
    id = 'tidyhq'
    name = 'TidyHQ'
    account_class = TidyHQAccount

    def extract_uid(self, data):
        return str(data.get('id'))

    def extract_common_fields(self, data):
        return data

    def get_default_scope(self):
        return []


provider_classes = [TidyHQProvider]
