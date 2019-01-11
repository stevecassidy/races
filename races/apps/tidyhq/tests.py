from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.tests import MockedResponse, TestCase

from .provider import TidyHQProvider


class TidyHQOAuth2Tests(OAuth2TestsMixin, TestCase):
    provider_id = TidyHQProvider.id

    def get_mocked_response(self):
        return MockedResponse(200, """{
    "id": 1,
    "first_name": "First",
    "last_name": "Last",
    "email": "first@example.com",
    "status":"active",
    "created_at": "2012-12-16T21:01:22Z"
  }""")  # noqa
