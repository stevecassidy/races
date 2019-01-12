from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import TidyHQProvider


urlpatterns = default_urlpatterns(TidyHQProvider)
