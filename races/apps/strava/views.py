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

import requests

from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)

from .provider import StravaProvider

class StravaOAuth2Adapter(OAuth2Adapter):
    provider_id = StravaProvider.id

    access_token_url = 'https://www.strava.com/oauth/token'
    authorize_url = 'https://www.strava.com/oauth/authorize'
    identity_url = 'https://www.strava.com/api/v3/athlete'

    def complete_login(self, request, app, token, **kwargs):
        extra_data = self.get_data(token.token)
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)

    def get_data(self, token):
        # Verify the user first
        resp = requests.get(
            self.identity_url,
            params={'access_token': token}
        )
        resp = resp.json()

        # Fill in their generic info
        info = {
                'username': "%s%s" % (resp.get('lastname'), resp.get('id')),
                'first_name': resp.get('firstname'),
                'last_name': resp.get('lastname'),
                'email': resp.get('email'),
                'id': resp.get('id')
        }

        return info


oauth2_login = OAuth2LoginView.adapter_view(StravaOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(StravaOAuth2Adapter)
