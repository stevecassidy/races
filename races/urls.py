from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from graphene_django.views import GraphQLView

admin.autodiscover()

urlpatterns = [
    url(r'', include('races.apps.cabici.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^graphql', GraphQLView.as_view(graphiql=True)),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
                      url(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns