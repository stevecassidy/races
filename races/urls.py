from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from rest_framework.authtoken import views as rstviews

admin.autodiscover()

urlpatterns = [
    url(r'', include('races.apps.cabici.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^api-token-auth/', rstviews.obtain_auth_token),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
                      url(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns