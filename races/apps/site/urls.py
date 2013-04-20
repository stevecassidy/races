from django.conf.urls import patterns, url


from races.apps.site import views

urlpatterns = patterns('',
    url(r'^$', views.HomePage.as_view(), name='home'),
    url(r'^races/$', views.ListRacesView.as_view(), name='races'),
    url(r'^races/(?P<year>\d{4})/(?P<month>[0-9][1-9])/$', views.ListRacesView.as_view(), name='racesmonth'),
    url(r'^races/(?P<pk>\d+)/$', views.RaceDetailView.as_view(), name='race'),
)
