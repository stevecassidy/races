#!/usr/bin/python
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.urls import path
from django.views.generic.base import TemplateView

from django.views.decorators.clickjacking import xframe_options_exempt
from races.apps.cabici import views, feeds, api


urlpatterns = [
    path('', views.HomePage.as_view(), name='home'),
    path('races/', views.RaceListDateView.as_view(), name='races'),
    path('races/<int:year>/<int:month>/', views.RaceListDateView.as_view(), name='racesmonth'),
    # path('races/<int:pk>/', views.RaceDetailView.as_view(), name='race'),

    path('races/<str:slug>/<int:pk>', views.RaceDetailView.as_view(), name='race'),
    path('races/<int:pk>/officials/', views.RaceOfficialUpdateView.as_view(), name='race_officials'),
    path('races/<int:pk>.xls', views.RaceSummarySpreadsheet.as_view(), name='race_summary_spreadsheet'),

    path('races/<int:pk>/update/', views.RaceUpdateView.as_view(), name='race_update'),
    path('races/<str:slug>/<int:pk>/results/', views.RaceUploadExcelView.as_view(), name='race_results_excel'),
    path('races/<str:slug>/<int:pk>/riders/', views.RaceRidersView.as_view(), name='race_riders'),

    path('feed', feeds.EventAtomFeed(), name='feed'),
    path('clubs/<str:slug>/feed', feeds.EventAtomFeed(), name='club_feed'),
    path('ical.ics', feeds.EventICALFeed(), name='ical'),
    path('clubs/<str:slug>/ical.ics', feeds.EventICALFeed(), name='club_ical'),

    path('clubs/', views.ClubListView.as_view(), name='clubs'),
    path('clubs/<str:slug>/', xframe_options_exempt(views.ClubDetailView.as_view()), name='club'),
    path('clubs/<str:slug>/dashboard/', views.ClubDashboardView.as_view(), name='club_dashboard'),
    path('clubs/<str:slug>/races/', views.ClubRacesView.as_view(), name='club_races'),
    path('clubs/<str:slug>/races/officials/', views.ClubRacesOfficalUpdateView.as_view(), name='club_races_officals'),
    path('clubs/<str:slug>/email/', views.ClubMemberEmailView.as_view(), name='club_email'),

    path('clubs/<str:slug>/races/publish/', views.RacePublishDraftView.as_view(), name='club_race_publish'),
    path('clubs/<str:slug>/results/', views.ClubRaceResultsView.as_view(), name='club_results'),
    path('clubs/<str:slug>/riders/', views.ClubRidersView.as_view(), name='club_riders'),
    path('clubs/<str:slug>/duty/', views.ClubDutyView.as_view(), name='club_duty'),
    path('clubs/<str:slug>/members.csv', views.club_riders_csv_view, name='club_members_csv'),
    path('clubs/<str:slug>/pointscore/', views.ClubPointscoreList.as_view(), name='pointscore_list'),
    path('clubs/<str:slug>/pointscore/<int:pk>', views.ClubPointscoreView.as_view(), name='pointscore'),
    path('clubs/<str:slug>/pointscore/<int:pk>/<int:rider>', views.ClubPointscoreAuditView.as_view(), name='pointscore-audit'),
    path('clubs/<str:slug>/riders/promotion/', views.ClubRidersPromotionView.as_view(), name='club_riders_promotion'),

    # get rider csv file for race entry front end
    path('clubs/<str:slug>/riders.xlsx', views.ClubRidersExcelView.as_view(), name='club_riders_excel'),

    path('riders/', views.RiderListView.as_view(), name='riders'),
    path('riders/<int:pk>', views.RiderView.as_view(), name='rider'),
    path('riders/<int:pk>/update', views.RiderUpdateView.as_view(), name='rider_update'),

    path('club/<str:slug>/ridergrade/<int:pk>/', views.ClubGradeView.as_view(), name='club_grade'),

    # api paths
    path('api/', api.api_root),
    path('api/token-auth/', api.CustomAuthToken.as_view()),

    path('api/clubs/', api.ClubList.as_view(), name='club-list'),
    path('api/clubs/<str:slug>/', api.ClubDetail.as_view(), name='club-detail'),
    path('api/clubroles/<slug:slug>/', api.UserRolesView.as_view(), name='club-roles'),
    path('api/clubroles/<slug:slug>/<int:pk>/', api.UserRoleDestroyView.as_view(), name='destroy-club-role'),
    path('api/races/', api.RaceList.as_view(), name='race-list'),
    path('api/races/<int:pk>/', api.RaceDetail.as_view(), name='race-detail'),
    path('api/racestaff/', api.RaceStaffList.as_view(), name='racestaff-list'),
    path('api/racestaff/<int:pk>/', api.RaceStaffDetail.as_view(), name='racestaff-detail'),
    path('api/racecourses/', api.RaceCourseList.as_view(), name='racecourse-list'),
    path('api/racecourses/<int:pk>/', api.RaceCourseDetail.as_view(), name='racecourse-detail'),

    path('api/riders/', api.RiderList.as_view(), name='rider-list'),
    path('api/riders/<int:pk>/', api.RiderDetail.as_view(), name='rider-detail'),
    # path('api/users/<int:pk>/', api.UserDetail.as_view(), name='user-detail'),

    path('api/pointscores/', api.PointScoreList.as_view(), name='pointscore-list'),
    path('api/pointscores/<int:pk>/', api.PointScoreDetail.as_view(), name='pointscore-detail'),
    path('api/raceresults/', api.RaceResultList.as_view(), name='raceresult-list'),
    path('api/raceresults/<int:pk>/', api.RaceResultDetail.as_view(), name='raceresult-detail'),

    path('test.html', TemplateView.as_view(template_name='test.html'))
]
