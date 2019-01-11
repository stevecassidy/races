import requests

from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)

from .provider import TidyHQProvider


class TidyHQOAuth2Adapter(OAuth2Adapter):
    provider_id = TidyHQProvider.id

    access_token_url = 'https://accounts.tidyhq.com/oauth/token'
    authorize_url = 'https://accounts.tidyhq.com/oauth/authorize'
    identity_url = 'https://accounts.tidyhq.com/oauth/contacts/me'

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
            'username': "%s%s" % (resp.get('last_name'), resp.get('id')),
            'first_name': resp.get('first_name'),
            'last_name': resp.get('lastname'),
            'email': resp.get('email'),
            'id': resp.get('id')
        }
        return info


oauth2_login = OAuth2LoginView.adapter_view(TidyHQOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(TidyHQOAuth2Adapter)
