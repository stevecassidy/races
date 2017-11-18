from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'', include('races.apps.cabici.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url('', include('django.contrib.auth.urls')),
    url('', include('social.apps.django_app.urls', namespace='social')),
]
