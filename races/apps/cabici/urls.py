from django.urls import path, re_path
from django.views.generic.base import TemplateView

from django.views.decorators.clickjacking import xframe_options_exempt
from races.apps.cabici import views, feeds, api


urlpatterns = [
    re_path(r'^$', views.HomePage.as_view(), name='home'),
    re_path(r'^races/$', views.RaceListDateView.as_view(), name='races'),
    re_path(r'^races/(?P<year>\d{4})/(?P<month>\d{2})/$', views.RaceListDateView.as_view(), name='racesmonth'),
    #re_path(r'^races/(?P<pk>\d+)/$', views.RaceDetailView.as_view(), name='race'),

    re_path(r'^races/(?P<slug>\w+)/(?P<pk>\d+)$', views.RaceDetailView.as_view(), name='race'),
    re_path(r'^races/(?P<pk>\d+)/officials/$', views.RaceOfficialUpdateView.as_view(), name='race_officials'),
    re_path(r'^races/(?P<pk>\d+).xls$', views.RaceSummarySpreadsheet.as_view(), name='race_summary_spreadsheet'),

    re_path(r'^races/(?P<pk>\d+)/update/$', views.RaceUpdateView.as_view(), name='race_update'),
    re_path(r'^races/(?P<slug>\w+)/(?P<pk>\d+)/results/$', views.RaceUploadExcelView.as_view(), name='race_results_excel'),
    re_path(r'^races/(?P<slug>\w+)/(?P<pk>\d+)/riders/$', views.RaceRidersView.as_view(), name='race_riders'),


    re_path(r'^feed', feeds.EventAtomFeed(), name='feed'),
    re_path(r'^clubs/(?P<slug>[^/]*)/feed', feeds.EventAtomFeed(), name='club_feed'),
    re_path(r'^ical.ics$', feeds.EventICALFeed(), name='ical'),
    re_path(r'^clubs/(?P<slug>[^/]*)/ical.ics', feeds.EventICALFeed(), name='club_ical'),

    re_path(r'^clubs/$', views.ClubListView.as_view(), name='clubs'),
    re_path(r'^clubs/(?P<slug>[^/]*)/$', xframe_options_exempt(views.ClubDetailView.as_view()), name='club'),
    re_path(r'^clubs/(?P<slug>[^/]*)/dashboard/$', views.ClubDashboardView.as_view(), name='club_dashboard'),
    re_path(r'^clubs/(?P<slug>[^/]*)/races/$', views.ClubRacesView.as_view(), name='club_races'),
    re_path(r'^clubs/(?P<slug>[^/]*)/races/officials/$', views.ClubRacesOfficalUpdateView.as_view(), name='club_races_officals'),
    re_path(r'^clubs/(?P<slug>[^/]*)/email/$', views.ClubMemberEmailView.as_view(), name="club_email"),

    re_path(r'^clubs/(?P<slug>[^/]*)/races/publish/$', views.RacePublishDraftView.as_view(), name='club_race_publish'),
    re_path(r'^clubs/(?P<slug>[^/]*)/results/$', views.ClubRaceResultsView.as_view(), name='club_results'),
    re_path(r'^clubs/(?P<slug>[^/]*)/riders/$', views.ClubRidersView.as_view(), name='club_riders'),
    re_path(r'^clubs/(?P<slug>[^/]*)/duty/$', views.ClubDutyView.as_view(), name='club_duty'),
    re_path(r'^clubs/(?P<slug>[^/]*)/members.csv$', views.club_riders_csv_view, name='club_members_csv'),
    re_path(r'^clubs/(?P<slug>[^/]*)/pointscore/$', views.ClubPointscoreList.as_view(), name="pointscore_list"),
    re_path(r'^clubs/(?P<slug>[^/]*)/pointscore/(?P<pk>\d+)$', views.ClubPointscoreView.as_view(), name='pointscore'),
    re_path(r'^clubs/(?P<slug>[^/]*)/pointscore/(?P<pk>\d+)/(?P<rider>\d+)$', views.ClubPointscoreAuditView.as_view(), name='pointscore-audit'),
    re_path(r'^clubs/(?P<slug>[^/]*)/riders/promotion/$', views.ClubRidersPromotionView.as_view(), name='club_riders_promotion'),

    # get rider csv file for race entry front end
    re_path(r'^clubs/(?P<slug>[^/]*)/riders.xlsx$', views.ClubRidersExcelView.as_view(), name='club_riders_excel'),


    re_path(r'^riders/$', views.RiderListView.as_view(), name='riders'),
    re_path(r'^riders/(?P<pk>\d+)$', views.RiderView.as_view(), name='rider'),
    re_path(r'^riders/(?P<pk>\d+)/update$', views.RiderUpdateView.as_view(), name='rider_update'),

    re_path(r'^club/(?P<slug>[^/]*)/ridergrade/(?P<pk>\d+)/$', views.ClubGradeView.as_view(), name='club_grade'),

    # api re_paths
    re_path(r'^api/$', api.api_root),
    re_path(r'^api/token-auth/', api.CustomAuthToken.as_view()),

    re_path(r'^api/clubs/$', api.ClubList.as_view(), name='club-list'),
    re_path(r'^api/clubs/(?P<slug>[^/]+)/$', api.ClubDetail.as_view(), name='club-detail'),
    path('api/clubroles/<slug:slug>/', api.UserRolesView.as_view(), name='club-roles'),
    path('api/clubroles/<slug:slug>/<int:pk>/', api.UserRoleDestroyView.as_view(), name='destroy-club-role'),
    re_path(r'^api/races/$', api.RaceList.as_view(), name='race-list'),
    re_path(r'^api/races/(?P<pk>[0-9]+)/$', api.RaceDetail.as_view(), name='race-detail'),
    re_path(r'^api/racestaff/$', api.RaceStaffList.as_view(), name='racestaff-list'),
    re_path(r'^api/racestaff/(?P<pk>[0-9]+)/$', api.RaceStaffDetail.as_view(), name='racestaff-detail'),
    re_path(r'^api/racecourses/$', api.RaceCourseList.as_view(), name='racecourse-list'),
    re_path(r'^api/racecourses/(?P<pk>[0-9]+)/$', api.RaceCourseDetail.as_view(), name='racecourse-detail'),

    re_path(r'^api/riders/$', api.RiderList.as_view(), name='rider-list'),
    re_path(r'^api/riders/(?P<pk>[0-9]+)/$', api.RiderDetail.as_view(), name='rider-detail'),
    #re_path(r'^api/users/(?P<pk>[0-9]+)/$', api.UserDetail.as_view(), name='user-detail'),

    re_path(r'^api/pointscores/$', api.PointScoreList.as_view(), name='pointscore-list'),
    re_path(r'^api/pointscores/(?P<pk>[0-9]+)/$', api.PointScoreDetail.as_view(), name='pointscore-detail'),
    re_path(r'^api/raceresults/$', api.RaceResultList.as_view(), name='raceresult-list'),
    re_path(r'^api/raceresults/(?P<pk>[0-9]+)/$', api.RaceResultDetail.as_view(), name='raceresult-detail'),

    re_path(r'^test.html$', TemplateView.as_view(template_name="test.html"))
]
