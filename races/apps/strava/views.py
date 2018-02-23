import requests

from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)

from .provider import StravaProvider

#https://www.strava.com/oauth/authorize?auth_type=reauthenticate&state=9hCgk7mfuNOE&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Faccounts%2Fstrava%2Flogin%2Fcallback%2F&response_type=code&client_id=5805&scope=email


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
