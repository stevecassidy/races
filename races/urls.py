from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from races.apps.cabici.api import CustomAuthToken

admin.autodiscover()

urlpatterns = [
    path('', include('races.apps.cabici.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('api-token-auth/', CustomAuthToken.as_view()),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns