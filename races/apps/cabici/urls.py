from django.conf.urls import patterns, url, include
from django.views.generic.base import TemplateView

from django.views.decorators.clickjacking import xframe_options_exempt


from races.apps.cabici import views, feeds, api


urlpatterns = [
    url(r'^$', views.HomePage.as_view(), name='home'),
    url(r'^races/$', views.RaceListDateView.as_view(), name='races'),
    url(r'^races/(?P<year>\d{4})/(?P<month>[0-9][1-9])/$', views.RaceListDateView.as_view(), name='racesmonth'),
    #url(r'^races/(?P<pk>\d+)/$', views.RaceDetailView.as_view(), name='race'),

    url(r'^races/(?P<slug>\w+)/(?P<pk>\d+)$', views.RaceDetailView.as_view(), name='race'),
    url(r'^races/(?P<pk>\d+)/officials/$', views.RaceOfficialUpdateView.as_view(), name='race_officials'),

    url(r'^races/(?P<pk>\d+)/update/$', views.RaceUpdateView.as_view(), name='race_update'),
    url(r'^races/(?P<slug>\w+)/(?P<pk>\d+)/results/$', views.RaceUploadExcelView.as_view(), name='race_results_excel'),
    url(r'^races/(?P<slug>\w+)/(?P<pk>\d+)/riders/$', views.RaceRidersView.as_view(), name='race_riders'),


    url(r'^feed', feeds.EventAtomFeed(), name='feed'),
    url(r'^clubs/(?P<slug>[^/]*)/feed', feeds.EventAtomFeed(), name='club_feed'),
    url(r'^ical.ics$', feeds.EventICALFeed(), name='ical'),
    url(r'^clubs/(?P<slug>[^/]*)/ical.ics', feeds.EventICALFeed(), name='club_ical'),

    url(r'^clubs/$', views.ClubListView.as_view(), name='clubs'),
    url(r'^clubs/(?P<slug>[^/]*)/$', xframe_options_exempt(views.ClubDetailView.as_view()), name='club'),
    url(r'^clubs/(?P<slug>[^/]*)/dashboard/$', views.ClubDashboardView.as_view(), name='club_dashboard'),
    url(r'^clubs/(?P<slug>[^/]*)/races/$', views.ClubRacesView.as_view(), name='club_races'),
    url(r'^clubs/(?P<slug>[^/]*)/races/officials/$', views.ClubRacesOfficalUpdateView.as_view(), name='club_races_officals'),
    url(r'^clubs/(?P<slug>[^/]*)/email/$', views.ClubMemberEmailView.as_view(), name="club_email"),

    url(r'^clubs/(?P<slug>[^/]*)/races/publish/$', views.RacePublishDraftView.as_view(), name='club_race_publish'),
    url(r'^clubs/(?P<slug>[^/]*)/results/$', views.ClubRaceResultsView.as_view(), name='club_results'),
    url(r'^clubs/(?P<slug>[^/]*)/riders/$', views.ClubRidersView.as_view(), name='club_riders'),
    url(r'^clubs/(?P<slug>[^/]*)/pointscore/(?P<pk>\d+)$', views.ClubPointscoreView.as_view(), name='pointscore'),
    url(r'^clubs/(?P<slug>[^/]*)/riders/promotion/$', views.ClubRidersPromotionView.as_view(), name='club_riders_promotion'),

    # get rider csv file for race entry front end
    url(r'^clubs/(?P<slug>[^/]*)/riders.xlsx$', views.ClubRidersExcelView.as_view(), name='club_riders_excel'),


    url(r'^riders/$', views.RiderListView.as_view(), name='riders'),
    url(r'^riders/(?P<pk>\d+)$', views.RiderView.as_view(), name='rider'),
    url(r'^riders/(?P<pk>\d+)/update$', views.RiderUpdateView.as_view(), name='rider_update'),

    url(r'^club/(?P<slug>[^/]*)/ridergrade/(?P<pk>\d+)/$', views.ClubGradeView.as_view(), name='club_grade'),

    # api urls
    url(r'^api/$', api.api_root),
    url(r'^api/clubs/$', api.ClubList.as_view(), name='club-list'),
    url(r'^api/clubs/(?P<slug>[^/]+)/$', api.ClubDetail.as_view(), name='club-detail'),
    url(r'^api/races/$', api.RaceList.as_view(), name='race-list'),
    url(r'^api/races/(?P<pk>[0-9]+)/$', api.RaceDetail.as_view(), name='race-detail'),
    url(r'^api/racestaff/$', api.RaceStaffList.as_view(), name='racestaff-list'),
    url(r'^api/racestaff/(?P<pk>[0-9]+)/$', api.RaceStaffDetail.as_view(), name='racestaff-detail'),
    url(r'^api/racecourses/$', api.RaceCourseList.as_view(), name='racecourse-list'),
    url(r'^api/racecourses/(?P<pk>[0-9]+)/$', api.RaceCourseDetail.as_view(), name='racecourse-detail'),

# no need for rider details through the API yet and danger of leaking user information
#    url(r'^api/riders/$', api.RiderList.as_view(), name='rider-list'),
#    url(r'^api/riders/(?P<pk>[0-9]+)/$', api.RiderDetail.as_view(), name='rider-detail'),
#    url(r'^api/users/(?P<pk>[0-9]+)/$', api.UserDetail.as_view(), name='user-detail'),

    url(r'^api/pointscores/$', api.PointScoreList.as_view(), name='pointscore-list'),
    url(r'^api/pointscores/(?P<pk>[0-9]+)/$', api.PointScoreDetail.as_view(), name='pointscore-detail'),
    url(r'^api/raceresults/$', api.RaceResultList.as_view(), name='raceresult-list'),
    url(r'^api/raceresults/(?P<pk>[0-9]+)/$', api.RaceResultDetail.as_view(), name='raceresult-detail'),

#    url(r'^test.html$', TemplateView.as_view(template_name="test.html"))
]
