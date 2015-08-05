from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^', include('races.apps.site.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url('^', include('django.contrib.auth.urls')),
    url('', include('social.apps.django_app.urls', namespace='social')),
    url(r"^account/", include("account.urls")),

)
