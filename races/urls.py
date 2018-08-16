from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from rest_framework.authtoken import views as rstviews

admin.autodiscover()

urlpatterns = [
    path('', include('races.apps.cabici.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('api-token-auth/', rstviews.obtain_auth_token),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns