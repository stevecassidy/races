#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
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

from races.apps.cabici import api, views

urlpatterns = [
    path("", views.HomePage.as_view(), name="home"),
    # api paths
    path("api/", api.api_root),
    path("api/token-auth/", api.CustomAuthToken.as_view()),
    path("api/clubs/", api.ClubList.as_view(), name="club-list"),
    path("api/clubs/<str:slug>/", api.ClubDetail.as_view(), name="club-detail"),
    path("api/clubroles/<slug:slug>/", api.UserRolesView.as_view(), name="club-roles"),
    path("api/clubroles/<slug:slug>/<int:pk>/", api.UserRoleDestroyView.as_view(), name="destroy-club-role"),
    path("api/races/", api.RaceList.as_view(), name="race-list"),
    path("api/races/<int:pk>/", api.RaceDetail.as_view(), name="race-detail"),
    path("api/racestaff/", api.RaceStaffList.as_view(), name="racestaff-list"),
    path("api/racestaff/<int:pk>/", api.RaceStaffDetail.as_view(), name="racestaff-detail"),
    path("api/racecourses/", api.RaceCourseList.as_view(), name="racecourse-list"),
    path("api/racecourses/<int:pk>/", api.RaceCourseDetail.as_view(), name="racecourse-detail"),
    path("api/riders/", api.RiderList.as_view(), name="rider-list"),
    path("api/riders/<int:pk>/", api.RiderDetail.as_view(), name="rider-detail"),
    # path('api/users/<int:pk>/', api.UserDetail.as_view(), name='user-detail'),
    path("api/pointscores/", api.PointScoreList.as_view(), name="pointscore-list"),
    path("api/pointscores/<int:pk>/", api.PointScoreDetail.as_view(), name="pointscore-detail"),
    path("api/raceresults/", api.RaceResultList.as_view(), name="raceresult-list"),
    path("api/raceresults/<int:pk>/", api.RaceResultDetail.as_view(), name="raceresult-detail"),
]
