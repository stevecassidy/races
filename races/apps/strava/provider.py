from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class StravaAccount(ProviderAccount):
    def get_avatar_url(self):
        return self.account.extra_data.get('user').get('image_192', None)

    def to_str(self):
        dflt = super(StravaAccount, self).to_str()
        return '%s (%s)' % (
            self.account.extra_data.get('name', ''),
            dflt,
        )


class StravaProvider(OAuth2Provider):
    id = 'strava'
    name = 'Strava'
    account_class = StravaAccount

    def extract_uid(self, data):
        return str(data.get('id'))

    def extract_common_fields(self, data):
        return data

    def get_default_scope(self):
        # scope should really be empty for read only but
        # leaving scope empty causes an error and there is
        # no way to not have it in the query string
        return ['view_private']


provider_classes = [StravaProvider]
