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
