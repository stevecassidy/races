from django.conf.urls import patterns, url, include

from races.apps.site import views
from races.apps.site import feeds

urlpatterns = patterns('',
    url(r'^$', views.HomePage.as_view(), name='home'),
    url(r'^races/$', views.ListRacesView.as_view(), name='races'),
    url(r'^races/(?P<year>\d{4})/(?P<month>[0-9][1-9])/$', views.ListRacesView.as_view(), name='racesmonth'),
    #url(r'^races/(?P<pk>\d+)/$', views.RaceDetailView.as_view(), name='race'),

    url(r'^races/(?P<slug>\w+)/(?P<pk>\d+)$', views.RaceDetailView.as_view(), name='race'),

    url(r'^races/(?P<pk>\d+)/update/$', views.RaceUpdateView.as_view(), name='race_update'),
    url(r'^races/(?P<pk>\d+)/delete/$', views.RaceDeleteView.as_view(), name='race_delete'),
    url(r'^races/create/$', views.create_races, name='race_create'),
    url(r'^races/(?P<slug>\w+)/(?P<pk>\d+)/results/$', views.RaceUploadCSVView.as_view(), name='race_results_csv'),

    url(r'^feed', feeds.EventAtomFeed(), name='feed'),

    url(r'^ical$', feeds.EventICALFeed(), name='ical'),
    url(r'^clubs/$', views.ClubListView.as_view(), name='clubs'),
    url(r'^clubs/(?P<slug>.*)/$', views.ClubDetailView.as_view(), name='club'),
    url(r'^clubs/(?P<slug>.*)/riders$', views.ClubRidersView.as_view(), name='clubriders'),

    url(r'^rider/(?P<pk>\d+)$', views.RiderView.as_view(), name='rider'),

    url(r'^test.html$', views.TestPageView.as_view(), name='test'),

)
